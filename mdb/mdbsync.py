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

import hashlib
import hmac
import json
import logging
import prologin.log
import prologin.mdb
import os
import time
import tornado.gen
import tornado.ioloop
import tornado.web
import yaml

from tornado.gen import Task


CFG = yaml.load(open(os.environ.get('MDBSYNC_CONFIG',
                                    '/etc/prologin/mdbsync.yml')))
if 'shared_secret' not in CFG:
    raise RuntimeError("Missing shared_secret in the YAML config")


class InternalPubSubQueue:
    def __init__(self):
        self.backlog = self.get_initial_backlog()
        self.subscribers = set()

    def get_initial_backlog(self):
        machines = prologin.mdb.connect(CFG.get('mdb', 'http://mdb/')).query()
        msg = { 'add': machines }
        return [json.dumps(msg)]

    def post_message(self, msg):
        logging.info('sending update message: %s' % msg)
        self.backlog.append(msg)
        for callback in self.subscribers:
            callback(msg)

    def register_subscriber(self, callback):
        logging.info("new subscriber arrived, sending the backlog")
        for msg in self.backlog:
            callback(msg)
        self.subscribers.add(callback)
        logging.info("added a new subscriber, count is now %d"
                         % len(self.subscribers))

    def unregister_subscriber(self, callback):
        self.subscribers.remove(callback)
        logging.info("removed a subscriber, count is now %d"
                         % len(self.subscribers))

ipsq = InternalPubSubQueue()


class PollHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        ipsq.register_subscriber(self.message_callback)

    def on_connection_close(self):
        ipsq.unregister_subscriber(self.message_callback)

    def message_callback(self, msg):
        self.write(msg + "\n")  # \n mostly for debugging (curl)
        self.flush()


class UpdateHandler(tornado.web.RequestHandler):
    def post(self):
        msg = self.get_argument("msg")
        ts = int(self.get_argument("ts"))
        provided_hmac = self.get_argument("hmac")

        s = str(len(msg)) + ':' + msg + str(ts)
        computed_hmac = hmac.new(CFG['shared_secret'].encode('utf-8'),
                                 msg=s.encode('utf-8'),
                                 digestmod=hashlib.sha256).hexdigest()
        if provided_hmac != computed_hmac:
            logging.error('received an update request with bad HMAC')
            self.send_error(500)
            return

        if not (time.time() - 5 < ts < time.time() + 5):
            logging.error('received an update request with bad timestamp')
            self.send_error(500)
            return

        ipsq.post_message(msg)


application = tornado.web.Application([
    (r"/poll", PollHandler),
    (r"/update", UpdateHandler),
])

if __name__ == '__main__':
    prologin.log.setup_logging('mdbsync')
    application.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
