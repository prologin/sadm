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
import aiohttp
import json
import prologin.timeauth
import socket
import urllib.request
import logging

from contextlib import closing
from urllib.parse import urljoin

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

    def __init__(self, base_url, secret=None, loop=None):
        self.base_url = base_url
        self.secret = secret
        self.loop = loop

    def _handle_exception(self, data):
        """Handle an exception from a remote call."""
        raise RemoteError(data['exn_type'], data['exn_message'])

    async def _call_method(self, method, args, kwargs):
        """Call the remote `method` passing `args` and `kwargs` to it.

        `args` must be a JSON-serializable list of positional arguments while
        `kwargs` must be a JSON-serializable dictionary of keyword arguments.

        Depending on what happens in the remote method, return a result, or
        raise a RemoteError. Raise an InternalError for anything else.
        """

        # Serialize arguments and send the request...
        arguments = {
            'args': args,
            'kwargs': kwargs,
        }

        # Generate the timeauth token
        if self.secret:
            arguments['hmac'] = prologin.timeauth.generate_token(self.secret,
                                                                 method)
        try:
            req_data = json.dumps(arguments)
        except (TypeError, ValueError):
            raise ValueError('non serializable argument types')

        url = urljoin(self.base_url, 'call/{}'.format(method))
        data = '{}\n'.format(req_data).encode('ascii')

        # FIXME(seirl): use a global session and async with?
        # This would require to have client as a context manager :/
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as req:
                return (await self._request_work(req))

    async def _request_work(self, req):
        if req.headers['Content-Type'] == 'application/json':
            # The remote call returned: we can have a result or an exception.
            result = await req.json()

            if result['type'] == 'result':
                # There is nothing more to do than returning the actual
                # result.
                return result['data']

            elif result['type'] == 'exception':
                # Just raise a RemoteError with interesting data.
                self._handle_exception(result)

            else:
                # There should not be any other possibility.
                raise InternalError(
                    'Invalid result type: {}'.format(result['type'])
                )
        else:
            # Something went wrong before reaching the remote procedure...
            raise InternalError(req.text)

    def __getattr__(self, method):
        """Return a callable to invoke a remote procedure."""
        async def proxy(*args, max_retries=0, retry_delay=10, **kwargs):
            for i in range(max_retries + 1):
                try:
                    return (await self._call_method(method, args, kwargs))
                except socket.error:
                    if i < max_retries:
                        logging.warning('<{}> down, cannot call {}. '
                            'Retrying in {}s...'.format(self.base_url,
                                method, retry_delay))
                        await asyncio.sleep(retry_delay)
                    else:
                        raise

        return proxy


class SyncClient(Client):
    def __getattr__(self, method):
        coro = super().__getattr__(method)

        def proxy(*args, **kwargs):
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(coro(*args, **kwargs))
            return res

        return proxy


class MetaClient:
    def __init__(self, client):
        self.client = client
