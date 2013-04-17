# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Pierre Bourdon <pierre.bourdon@prologin.org>
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

"""MDBSync server: sends MDB changes to MDBSync clients via long polling
connections. Uses Tornado to be able to support an arbitrary number of clients.
"""

import time
import tornado.gen
import tornado.ioloop
import tornado.web

from tornado.gen import Task

class PollHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        for i in range(100):
            self.write("%d\n" % i)
            self.flush()
            yield Task(tornado.ioloop.IOLoop.instance().add_timeout,
                       time.time() + 1)

application = tornado.web.Application([
    (r"/poll", PollHandler),
])

if __name__ == '__main__':
    application.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
