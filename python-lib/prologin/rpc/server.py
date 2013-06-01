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

import http.server
import json
import re
import types


class MethodError(Exception):
    """Exception used to notice the remote callers that the requested method
    does not exist.
    """
    pass


def remote_method(func):
    """Decorator for methods to be callable remotely."""
    func.remote_method = True
    return func

def is_remote_method(obj):
    """Return if a random object is a remote method."""
    return callable(obj) and getattr(obj, 'remote_method', False)


class MethodCollection(type):
    """Metaclass for RPC servers: collect remote methods and store them in a
    class-wide REMOTE_METHOD dictionnary.  Be careful: of course, stored
    methods are not bound to an instance.
    """

    def __init__(cls, name, bases, dct):
        super(MethodCollection, cls).__init__(name, bases, dct)

        # Build the list of remote methods.
        remote_methods = {}
        for name, obj in dct.items():
            if is_remote_method(obj):
                remote_methods[name] = obj
        cls.REMOTE_METHODS = remote_methods


class RequestHandler(http.server.BaseHTTPRequestHandler):

    METHOD_CALL = re.compile(r'/call/([0-9a-zA-Z_]+)')
    PING        = re.compile(r'/ping')
    THREADS     = re.compile(r'/threads')
    HELP        = re.compile(r'/help')

    def do_POST(self):
        line = self.rfile.readline().strip().decode('ascii')
        request = json.loads(line)
        handlers = {
            self.METHOD_CALL: self.handle_method_call,
            self.PING:        self.handle_ping,
            self.THREADS:     self.handle_threads,
            self.HELP:        self.handle_help,
        }

        # Look for a specific handler for this request...
        for pattern, handler in handlers.items():
            m = pattern.match(self.path)
            if m:
                return handler(request, *m.groups())

        # If no one was found, return an error.
        self.send_error(404, 'Invalid resource')

    def _send_json_line(self, data):
        self.wfile.write(json.dumps(data).encode('ascii'))
        self.wfile.write(b'\n')
        self.wfile.flush()

    def _send_exception(self, exn):
        self._send_json_line({
            'type': 'exception',
            'exn_type': type(exn).__name__,
            'exn_message': str(exn),
        })

    def _send_result_data(self, data):
        success = True
        try:
            self._send_json_line({
                'type': 'result',
                'data': data,
            })
        except (TypeError, ValueError):
            self._send_exception(
                ValueError('The remote method returned something not JSON'),
                False
            )
            success = False
        return success

    def handle_method_call(self, request, method_name):
        self.send_response(200)
        self.end_headers()

        # First get the method to call.
        try:
            method = self.server.REMOTE_METHODS[method_name]
        except KeyError:
            return self._send_exception(MethodError(method_name))

        args = request['args']
        kwargs = request['kwargs']

        # Actually call it.
        try:
            result = method(self.server, *args, **kwargs)
        except Exception as exn:
            return self._send_exception(exn)

        # The remote method can be a generator (returns a sequence of values),
        # or just some regular function (returns only one value).
        if isinstance(result, types.GeneratorType):
            # If it is a generator, notice the client.
            self._send_json_line({'type': 'generator'})

            # Then yield successive values.
            while True:
                try:
                    value = next(result)
                except StopIteration:
                    # The generator stopped: notice the client and stop, too.
                    return self._send_json_line({'type': 'stop'})
                except Exception as exn:
                    # The generator raised an error: transmit it to the client
                    # and stop.
                    return self._send_exception(exn)
                else:
                    # The generator simply yielded a value: transmit it to the
                    # client, or stop there if this is some non-JSON data.
                    if not self._send_result_data(value):
                        return

        else:
            # Otherwise, just return the single value.
            self._send_result_data(result)


    def handle_ping(self, request):
        raise NotImplementedError()

    def handle_threads(self, request):
        raise NotImplementedError()

    def handle_help(self, request):
        raise NotImplementedError()


class BaseServer(http.server.HTTPServer, metaclass=MethodCollection):
    """RPC base server: let clients call remotely subclasses methods.

    Just subclass me, add some remote methods using the `remote_method`
    decorator and instanciate me!
    """

    def __init__(self, server_address):
        super(BaseServer, self).__init__(server_address, RequestHandler)
