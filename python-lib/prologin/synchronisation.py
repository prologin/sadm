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

"""Synchronisation client/server library: sends updates to clients via long
polling connections.  Uses Tornado to be able to support an arbitrary number of
clients.
"""


import hashlib
import hmac
import json
import logging
import requests
import time
import tornado.ioloop
import tornado.web
import urllib.parse
import urllib.request


class InternalPubSubQueue:
    """Maintain a backlog of updates. Used by the server.
    """
    def __init__(self, initial_backlog):
        # TODO(delroth): implem regular backlog packing to remove duplicates
        self.backlog = list(initial_backlog)
        self.subscribers = set()

    def post_message(self, msg):
        logging.info('sending update message: %s' % msg)
        self.backlog.extend(msg)
        for callback in self.subscribers:
            callback(json.dumps(msg))

    def register_subscriber(self, callback):
        logging.info("new subscriber arrived, sending the backlog")
        callback(json.dumps(self.backlog))
        self.subscribers.add(callback)
        logging.info("added a new subscriber, count is now %d"
                         % len(self.subscribers))

    def unregister_subscriber(self, callback):
        self.subscribers.remove(callback)
        logging.info("removed a subscriber, count is now %d"
                         % len(self.subscribers))


class PollHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.application.pubsub_queue.register_subscriber(
            self.message_callback
        )

    def on_connection_close(self):
        self.application.pubsub_queue.unregister_subscriber(
            self.message_callback
        )

    def message_callback(self, msg):
        self.write(msg + "\n")  # \n mostly for debugging (curl)
        self.flush()


class UpdateHandler(tornado.web.RequestHandler):
    def post(self):
        msg = self.get_argument("msg")
        ts = int(self.get_argument("ts"))
        provided_hmac = self.get_argument("hmac")

        s = str(len(msg)) + ':' + msg + str(ts)
        computed_hmac = hmac.new(self.application.shared_secret,
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

        self.application.pubsub_queue.post_message(json.loads(msg))


class Server(tornado.web.Application):
    """Synchronisation server. Users must derive from this class and implement
    required methods.
    """

    def __init__(self, shared_secret, port):
        """The `shared_secret` is used to restrict clients that can add
        updates.
        """
        super(Server, self).__init__([
            (r'/poll', PollHandler),
            (r'/update', UpdateHandler),
        ])
        self.port = port
        self.shared_secret = shared_secret.encode('utf-8')
        while True:
            try:
                backlog = self.get_initial_backlog()
                break
            except Exception:
                logging.exception('unable to get the backlog, retrying in 2s')
                time.sleep(2)
        self.pubsub_queue = InternalPubSubQueue(backlog)

    def start(self):
        """Run the server."""
        self.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()

    def get_initial_backlog(self):
        """Return the initial state of updates as a list.

        Users must give an implementation for this method.
        """
        raise NotImplementedError()


class Client:
    """Synchronisation client.
    """

    def __init__(self, url, secret=None, pk=None):
        self.url = url
        self.secret = secret
        self.pk = pk

    def send_update(self, update):
        self.send_updates([update])

    def send_updates(self, updates):
        if self.secret is None:
            raise ValueError("No secret provided, can't send update")

        msg = json.dumps(updates)
        ts = int(time.time())
        s = str(len(msg)) + ':' + msg + str(ts)
        hm = hmac.new(self.secret.encode('utf-8'), msg=s.encode('utf-8'),
                      digestmod=hashlib.sha256)
        hm = hm.hexdigest()

        r = requests.post(urllib.parse.urljoin(self.url, '/update'),
                          data={ 'msg': msg, 'ts': ts, 'hmac': hm })
        if r.status_code != 200:
            raise RuntimeError("Unable to post an update")

    def poll_updates(self, callback):
        if self.pk is None:
            raise ValueError('No primary key field name specified')
        while True:
            state = {}  # indexed by mac
            poll_url = urllib.parse.urljoin(self.url, '/poll')
            try:
                with urllib.request.urlopen(poll_url) as resp:
                    while True:
                        try:
                            l = resp.readline().decode('utf-8').strip()
                            updates = json.loads(l)
                        except Exception:
                            logging.exception('could not decode updates')
                            break
                        for update in updates:
                            data = update['data']
                            if update['type'] == 'update':
                                state[data[self.pk]] = data
                            elif update['type'] == 'delete':
                                if not data[self.pk] in state:
                                    logging.error('removing unexisting data')
                                else:
                                    del state[self.pk]
                        try:
                            callback(state.values())
                        except Exception:
                            logging.exception(
                                'error in the synchorisation client callback'
                            )
            except Exception:
                logging.error(
                    'connection lost to synchronisation server, retrying in 2s'
                )
                time.sleep(2)
