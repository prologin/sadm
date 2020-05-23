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

import functools
import inspect
import json
import logging
import sys
import traceback

import aiohttp.web

import prologin.timeauth
import prologin.web
from prologin.rpc import monitoring


class MethodError(Exception):
    """Exception used to notice the remote callers that the requested method
    does not exist.
    """

    pass


class BadToken(Exception):
    """Exception used to notice the remote callers that the timeauth token
    is wrong or has expired.
    """

    pass


class MissingToken(Exception):
    """Exception used to notice the remote callers that the timeauth token
    cannot be found in the request.
    """

    pass


def remote_method(func=None, *, auth_required=True):
    """Decorator for methods to be callable remotely."""
    if func is None:
        return functools.partial(remote_method, auth_required=auth_required)
    func.remote_method = True
    func.auth_required = auth_required
    return func


def is_remote_method(obj):
    """Return if a random object is a remote method."""
    return callable(obj) and getattr(obj, "remote_method", False)


class MethodCollection(type):
    """Metaclass for RPC objects: collect remote methods and store them in a
    class-wide REMOTE_METHOD dictionnary.  Be careful: of course, stored
    methods are not bound to an instance.
    """

    def __init__(cls, name, bases, dct):
        super(MethodCollection, cls).__init__(name, bases, dct)

        # Build the list of remote methods.
        remote_methods = {}
        for name, obj in dct.items():
            if is_remote_method(obj):
                if not (
                    inspect.iscoroutinefunction(obj)
                    or inspect.isasyncgenfunction(obj)
                ):
                    raise RuntimeError(
                        f"Remote method {obj} is not a coroutine."
                    )
                remote_methods[name] = obj
        cls.REMOTE_METHODS = remote_methods


class RemoteCallHandler:
    def __init__(self, request):
        self.request = request
        self.secret = self.request.app.secret
        self.method_name = request.match_info["name"]

    @property
    def rpc_object(self):
        """RPC object: contains method that can be called remotely."""
        return self.request.app.rpc_object

    async def _get_method(self):
        try:
            return self.rpc_object.REMOTE_METHODS[self.method_name]
        except KeyError:
            self._raise_exception(
                MethodError(self.method_name),
                http_error=aiohttp.web.HTTPNotFound,
            )

    def _log_call(self, data):
        peername = self.request.transport.get_extra_info("peername")
        elide = 10

        def farg(a):
            if isinstance(a, str) and len(a) > elide:
                a = f"{a[:elide]}…"
            return repr(a)

        logging.debug(
            "RPC <%s> %s(%s%s)",
            peername,
            self.method_name,
            ", ".join(farg(a) for a in data["args"]),
            ", ".join(
                f"{farg(k)}={farg(v)}" for k, v in data["kwargs"].items()
            ),
        )

    async def _check_secret(self, data):
        if self.secret is not None:
            if "hmac" not in data or not data["hmac"]:
                self._raise_exception(
                    MissingToken(self.method_name),
                    http_error=aiohttp.web.HTTPBadRequest,
                )
            token = data["hmac"]
            r = prologin.timeauth.check_token(
                token, self.secret, self.method_name
            )
            if not r:
                self._raise_exception(
                    BadToken(self.method_name),
                    http_error=aiohttp.web.HTTPForbidden,
                )

    @monitoring._observe_rpc_call_in
    async def __call__(self):
        data = {"args": [], "kwargs": {}}
        if self.request.method == "POST":
            try:
                r = await self.request.json()
                data.update(r)
            except json.decoder.JSONDecodeError as exn:
                self._raise_exception(exn)

        self._log_call(data)

        method = await self._get_method()
        if method.auth_required:
            await self._check_secret(data)

        coroutine = method(self.rpc_object, *data["args"], **data["kwargs"])
        if inspect.isasyncgenfunction(method):
            return await self._call_generator_method(coroutine)

        return await self._call_method(coroutine)

    async def _call_method(self, coroutine):
        try:
            result = await coroutine
            body = self._json_encode(self._format_result(result))
            return aiohttp.web.Response(
                body=body, content_type="application/json",
            )
        except Exception as exn:
            logging.exception("Remote method %s raised:", self.method_name)
            tb = sys.exc_info()[2]
            self._raise_exception(exn, tb)

    async def _call_generator_method(self, generator):
        response = aiohttp.web.StreamResponse(
            headers={"Content-Type": "application/json; generator"}
        )
        await response.prepare(self.request)
        try:
            async for result in generator:
                await response.write(
                    self._json_encode(self._format_result(result))
                )
        except Exception as exn:
            logging.exception(
                "Remote generator method %s raised:", self.method_name
            )
            # We cannot raise a proper HTTP error since we already sent
            # headers.
            tb = sys.exc_info()[2]
            await response.write(
                self._json_encode(self._format_exception(exn, tb))
            )
        await response.write_eof()

    def _format_exception(self, exn, tb=None):
        return {
            "type": "exception",
            "exn_type": type(exn).__name__,
            "exn_message": str(exn),
            "exn_traceback": traceback.format_tb(tb),
        }

    def _raise_exception(
        self, exn, tb=None, http_error=aiohttp.web.HTTPInternalServerError
    ):
        body = self._json_encode(self._format_exception(exn, tb))
        raise http_error(body=body, content_type="application/json")

    def _format_result(self, result):
        return {"type": "result", "data": result}

    def _json_encode(self, data):
        return json.dumps(data).encode() + b"\n"


class BaseRPCApp(prologin.web.AiohttpApp, metaclass=MethodCollection):
    """RPC base application: let clients call remotely subclasses methods.

    Just subclass me, add some remote methods using the `remote_method`
    decorator and instantiate me!
    """

    def __init__(self, secret=None, **kwargs):
        async def handler(request):
            print(request.url)
            print(request.headers)
            return await RemoteCallHandler(request)()

        super().__init__(
            [("*", r"/call/{name:[0-9a-zA-Z_]+}", handler)],
            client_max_size=1024 * 1024 * 1024 * 1,
            **kwargs,
        )
        self.app.secret = secret
        self.app.rpc_object = self
