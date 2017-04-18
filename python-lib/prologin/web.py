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

This initializes logging using prologin.log, and maps some special URLs to
useful pages:
  * /__ping
    Should always return the string "pong". Used for health checking.
  * /__threads
    Shows the status of all threads in the process and their current stack.
  * [TODO] /__monitoring
    Exports monitoring values for outside use.
"""

import asyncio
import aiohttp.web
import sys
import tornado.web
import traceback


def exceptions_catched(func):
    """Decorator for function handlers: return a HTTP 500 error when an
    exception is raised.
    """
    def wrapper():
        try:
            return (200, 'OK') + func()
        except Exception:
            return (
                500, 'Error',
                {'Content-Type': 'text/html'},
                '<h1>Onoes, internal server error</h1>'
            )
    return wrapper

@exceptions_catched
def ping_handler():
    return { 'Content-Type': 'text/plain' }, "pong"

@exceptions_catched
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
        status_code, reason, headers, content = handler()
        start_response(
            '{} {}'.format(status_code, reason),
            list(headers.items())
        )
        return [content.encode('utf-8')]


class TornadoApp(tornado.web.Application):
    def __init__(self, handlers, app_name):
        # Prepend special handlers, taking care of the Tornado interfacing.
        handlers = (
            tuple(
                (path, self.get_special_handler(handler))
                for path, handler in HANDLED_URLS.items()
            )
            + tuple(handlers)
        )
        super(TornadoApp, self).__init__(handlers)
        self.app_name = app_name

        # TODO(delroth): initialize logging

    def get_special_handler(self, handler_func):
        """Wrap a special handler into a Tornado-compatible handler class."""

        class SpecialHandler(tornado.web.RequestHandler):
            """Wrapper handler for special resources.
            """
            def get(self):
                status_code, reason, headers, content = handler_func()
                self.set_status(status_code, reason)
                for name, value in headers.items():
                    self.set_header(name, value)
                self.write(content.encode('utf-8'))

        return SpecialHandler


class AiohttpApp:
    def __init__(self, routes, app_name, loop=None):
        self.app = aiohttp.web.Application()
        self.app_name = app_name
        # TODO(seirl): integrate with HANDLED_URLS
        for route in routes:
            self.app.router.add_route(*route)
        self.loop = loop or asyncio.get_event_loop()

    def run(self, **kwargs):
        aiohttp.web.run_app(self.app, loop=self.loop, **kwargs)
