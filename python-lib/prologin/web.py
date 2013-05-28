# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Association Prologin <info@prologin.org>
#
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

"""Provides utilities for Prologin web applications. Everything should be
prologinized like this:

    # WSGI application
    import prologin.web
    application = prologin.web.WsgiApp(application, 'app_name')

    # Tornado application
    import prologin.web
    application = prologin.web.TornadoApp(handlers, 'app_name')

    # BaseHTTPServer application
    class MyRequestHandler(prologin.web.ProloginBaseHTTPRequestHandler):
        ...

If your application is an RPC server, this is handled automatically.

This initializes logging using prologin.log, and maps some special URLs to
useful pages:
  * /__ping
    Should always return the string "pong". Used for health checking.
  * /__threads
    Shows the status of all threads in the process and their current stack.
  * [TODO] /__monitoring
    Exports monitoring values for outside use.
"""

import sys
import traceback

def ping_handler():
    return { 'Content-Type': 'text/plain' }, "pong"

def threads_handler():
    frames = sys._current_frames()
    text = ['%d threads found\n\n' % len(frames)]
    for i, frame in frames.items():
        s = 'Thread 0x%x:\n%s\n' % (i, ''.join(traceback.format_stack(frame)))
        text.append(s)
    return { 'Content-Type': 'text/plain' }, ''.join(text)

HANDLED_URLS = {
    '/__ping': ping_handler,
    '/__threads': threads_handler,
}

class WsgiApp:
    def __init__(self, app, app_name):
        self.app = app
        self.app_name = app_name

        # TODO(delroth): initialize logging

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'] in HANDLED_URLS:
            handler = HANDLED_URLS[environ['PATH_INFO']]
            return self.call_handler(environ, start_response, handler)
        return self.app(environ, start_response)

    def call_handler(self, environ, start_response, handler):
        try:
            headers, text = handler()
            start_response('200 OK', list(headers.items()))
            return [text.encode('utf-8')]
        except Exception:
            start_response('500 Error', [('Content-Type', 'text/html')])
            return [b'<h1>Onoes, internal server error.</h1>']
