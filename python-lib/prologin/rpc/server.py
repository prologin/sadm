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

import aiohttp.web
import functools
import inspect
import json
import logging
import sys
import traceback

import prologin.web

from . import monitoring


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
    return callable(obj) and getattr(obj, 'remote_method', False)


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
                if not inspect.iscoroutinefunction(obj):
                    raise RuntimeError("Remote method {} is not a coroutine"
                                       .format(obj))
                remote_methods[name] = obj
        cls.REMOTE_METHODS = remote_methods


class RemoteCallHandler:
    def __init__(self, request):
        self.request = request
        self.secret = self.request.app.secret
        self.method_name = request.match_info['name']

    @property
    def rpc_object(self):
        """RPC object: contains method that can be called remotely."""
        return self.request.app.rpc_object

    @monitoring._observe_rpc_call_in
    async def __call__(self):
        data = {'args': [], 'kwargs': {}}
        if self.request.method == 'POST':
            try:
                data.update(await self.request.json())
            except json.decoder.JSONDecodeError as exn:
                self._raise_exception(exn)

        self._log_call(data)

        method = await self._get_method()
        if method.auth_required:
            await self._check_secret(data)

        result = await self._call_method(method, data)

        return (await self._send_result_data(result))

    def _log_call(self, data):
        peername = self.request.transport.get_extra_info('peername')

        def farg(a):
            if isinstance(a, str) and len(a) > 10:
                a = a[:10] + '…'
            return repr(a)

        logging.debug('RPC <{}> {}({}{})'.format(
            peername,
            self.method_name,
            ', '.join([farg(a) for a in data['args']]),
            ', '.join([farg(a) + '=' + farg(b)
                       for a, b in data['kwargs'].items()])))

    async def _check_secret(self, data):
        if self.secret is not None:
            if 'hmac' not in data or not data['hmac']:
                self._raise_exception(MissingToken(self.method_name),
                                      http_error=aiohttp.web.HTTPBadRequest)
            token = data['hmac']
            r = prologin.timeauth.check_token(token, self.secret,
                                              self.method_name)
            if not r:
                self._raise_exception(BadToken(self.method_name),
                                      http_error=aiohttp.web.HTTPForbidden)

    async def _get_method(self):
        try:
            return self.rpc_object.REMOTE_METHODS[self.method_name]
        except KeyError:
            self._raise_exception(MethodError(self.method_name),
                                  http_error=aiohttp.web.HTTPNotFound)

    async def _call_method(self, method, data):
        args = data['args']
        kwargs = data['kwargs']

        try:
            return (await method(self.rpc_object, *args, **kwargs))
        except Exception as exn:
            logging.exception('Remote method %s raised:', self.method_name)
            tb = sys.exc_info()[2]
            self._raise_exception(exn, tb)

    async def _send_json(self, data):
        return aiohttp.web.Response(body=json.dumps(data).encode() + b'\n',
                                    content_type='application/json')

    def _raise_exception(self, exn, tb=None,
                         http_error=aiohttp.web.HTTPInternalServerError):
        data = {
            'type': 'exception',
            'exn_type': type(exn).__name__,
            'exn_message': str(exn),
            'exn_traceback': traceback.format_tb(tb),
        }
        body = json.dumps(data).encode() + b'\n'
        raise http_error(body=body, content_type='application/json')

    async def _send_result_data(self, data):
        try:
            return (await self._send_json({
                'type': 'result',
                'data': data,
            }))
        except (TypeError, ValueError):
            self._raise_exception(
                ValueError('The remote method returned something not JSON'),
            )


class BaseRPCApp(prologin.web.AiohttpApp, metaclass=MethodCollection):
    """RPC base application: let clients call remotely subclasses methods.

    Just subclass me, add some remote methods using the `remote_method`
    decorator and instanciate me!
    """

    def __init__(self, app_name, secret=None, **kwargs):
        async def handler(request):
            return (await RemoteCallHandler(request)())

        super().__init__([
            ('*', r'/call/{name:[0-9a-zA-Z_]+}', handler),
        ], app_name, **kwargs)
        self.app.secret = secret
        self.app.rpc_object = self
