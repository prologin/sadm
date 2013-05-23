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

"""Provides WSGI utilities for Prologin web applications. Everything should be
prologinized like this:

    import prologin.wsgi
    application = prologin.wsgi.ProloginWebApp(application, 'app_name')

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

class ProloginWebApp:
    def __init__(self, app, app_name):
        self.app = app
        self.app_name = app_name

        # TODO(delroth): initialize logging

    def __call__(self, environ, start_response):
        HANDLED_URLS = {
            '/__ping': self.ping_handler,
            '/__threads': self.threads_handler,
        }
        if environ['PATH_INFO'] in HANDLED_URLS:
            handler = HANDLED_URLS[environ['PATH_INFO']]
            return handler(environ, start_response)
        return self.app(environ, start_response)

    def ping_handler(self, environ, start_response):
        """Always returns "pong" to be able to easily check if an application
        is up."""
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [b"pong"]

    def threads_handler(self, environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        frames = sys._current_frames()
        yield '
        for i, frame in frames.items():
            s = 'Thread 0x%x:\n%s\n' % (i,
                                        ''.join(traceback.format_stack(frame)))
            yield s.encode('utf-8')
