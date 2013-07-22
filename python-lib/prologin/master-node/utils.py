# -*- encoding: utf-8 -*-
# This file is part of Stechec.
#
# Copyright (c) 2011 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2011 Association Prologin <info@prologin.org>
#
# Stechec is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Stechec is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Stechec.  If not, see <http://www.gnu.org/licenses/>.

import psycopg2
import psycopg2.extensions
import tornado.ioloop
import tornado.gen

"""
Implements a wait function for Psycopg in order to wait for events while being
nice with tornado (not blocking, etc.).

See http://initd.org/psycopg/docs/advanced.html#asynchronous-support
and https://gist.github.com/FSX/861193
"""

ioloop = tornado.ioloop.IOLoop.instance()

def init_psycopg_tornado():

    @tornado.gen
    def wait(conn, timeout=None):
        while True:
            state = conn.poll()
            if state == psycopg2.extensions.POLL_OK:
                break
            elif state == psycopg2.extensions.POLL_READ:
                ioloop.add_handler(conn.fileno(),
                                   (yield gen.Callback('read_psycopg2')),
                                   tornado.ioloop.IOLoop.READ)
                yield tornado.gen.Wait('read_psycopg2')
            elif state == psycopg2.extensions.POLL_WRITE:
                ioloop.add_handler(conn.fileno(),
                                   (yield gen.Callback('write_psycopg2')),
                                   tornado.ioloop.IOLoop.WRITE)
                yield tornado.gen.Wait('write_psycopg2')
            else:
                raise psycopg2.OperationalError("invalid poll state")

    psycopg2.extensions.set_wait_callback(wait)
