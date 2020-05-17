# Prologin-SADM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prologin-SADM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prologin-SADM.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import contextlib
import json
import logging
import socket
from urllib.parse import urljoin

import aiohttp

import prologin.timeauth


class BaseError(Exception):
    """Base class for all exceptions here."""

    pass


class InternalError(BaseError):
    """Raised when there is a protocol failure somewhere."""

    pass


class RemoteError(BaseError):
    """Raised when the remote procedure raised an error."""

    def __init__(self, type, message):
        self.type = type
        self.message = message
        super(RemoteError, self).__init__(type, message)


class Client:
    """RPC client: connect to a server and perform remote calls."""

    def __init__(self, base_url, secret=None, http_client=None):
        self._base_url = base_url
        self._secret = secret
        # For testing & context(), we have to use an existing client.
        self._http_client = http_client

    @contextlib.asynccontextmanager
    async def _client(self):
        if self._http_client is not None:
            # The lifecycle of existing clients are handled externally. It's
            # important not to close (__aexit__) them ourselves.
            yield self._http_client
            return

        # FIXME(seirl): use a global session and async with?
        # This would require to have client as a context manager :/
        async with aiohttp.client.ClientSession() as client:
            yield client

    def _call_params(self, method, args, kwargs):
        arguments = {"args": args, "kwargs": kwargs}
        if self._secret:
            arguments["hmac"] = prologin.timeauth.generate_token(
                self._secret, method
            )
        url = urljoin(self._base_url, f"call/{method}")
        return url, arguments

    async def _call_method(self, method, args, kwargs):
        """Calls the remote `method` passing `args` and `kwargs` to it.

        `args` must be a JSON-serializable list of positional arguments while
        `kwargs` must be a JSON-serializable dictionary of keyword arguments.

        Depending on the nature and behavior of the remote method, either:
            * returns a result;
            * returns a async context that gives an async generator of results;
            * raises a RemoteError.

        Raises an InternalError for any error that isn't caused by the remote.
        """
        url, data = self._call_params(method, args, kwargs)

        stack = contextlib.AsyncExitStack()
        client = await stack.enter_async_context(self._client())
        try:
            resp = await stack.enter_async_context(client.post(url, json=data))
        except (TypeError, ValueError):
            await stack.aclose()
            raise ValueError(
                f"JSON cannot encode argument types: {args:r}, {kwargs:r}"
            )

        content_type = resp.headers["Content-Type"]

        if content_type == "application/json; generator":
            return self._generator_context(stack, resp)
        elif content_type == "application/json":
            try:
                result = await resp.json()
                return self._parse_response(result)
            finally:
                await stack.aclose()
        else:
            await stack.aclose()
            raise InternalError(f"Unknown Content-Type: '{content_type}'.")

    def _parse_response(self, result):
        result_type = result["type"]
        if result_type == "result":
            # There is nothing more to do than returning the actual result.
            return result["data"]
        elif result_type == "exception":
            # Just raise a RemoteError with interesting data.
            self._handle_exception(result)
        else:
            # There should not be any other possibility.
            raise InternalError(f"Invalid result type: {result_type}")

    def _handle_exception(self, data):
        """Handle an exception from a remote call."""
        raise RemoteError(data["exn_type"], data["exn_message"])

    @contextlib.asynccontextmanager
    async def _generator_context(self, stack, resp):
        async def generator():
            async for line in resp.content:
                yield self._parse_response(json.loads(line))

        yield generator()
        await stack.aclose()

    def __getattr__(self, method):
        """Returns a callable to invoke a remote procedure."""

        async def proxy(*args, max_retries=0, retry_delay=10, **kwargs):
            for i in range(max_retries + 1):
                try:
                    return await self._call_method(method, args, kwargs)
                except socket.error:
                    if i < max_retries:
                        logging.warning(
                            "<%s> down, cannot call %s. Retrying in %ss...",
                            self._base_url,
                            method,
                            retry_delay,
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        raise

        return proxy


class SyncClient(Client):
    def __getattr__(self, method):
        func = super().__getattr__(method)
        loop = asyncio.new_event_loop()

        def proxy(*args, **kwargs):
            try:
                return loop.run_until_complete(func(*args, **kwargs))
            finally:
                loop.close()

        return proxy
