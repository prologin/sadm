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


import json
import logging
import prologin.timeauth
import requests
import time
import tornado.ioloop
import tornado.web
import urllib.parse
import urllib.request


def update_backlog(pk, backlog, updates):
    for update in updates:
        data = update['data']
        key = data[pk]
        if update['type'] == 'update':
            backlog[key] = data
        elif update['type'] == 'detele':
            if backlog.pop(key, None) is None:
                logging.error('removing unexisting data')
        else:
            logging.error('invalid update type: {}'.format(update['type']))

def items_to_updates(items):
    return [
        {'type': 'update', 'data': item}
        for item in items
    ]


class InternalPubSubQueue:
    """Maintain a backlog of updates. Used by the server.
    """
    def __init__(self, pk, initial_backlog):
        self.pk = pk
        self.backlog = {}
        self.subscribers = set()
        self.update_backlog(items_to_updates(initial_backlog))

    def update_backlog(self, updates):
        update_backlog(self.pk, self.backlog, updates)

    def post_message(self, msg):
        logging.info('sending update message: %s' % msg)
        self.update_backlog(msg)
        for callback in self.subscribers:
            callback(json.dumps(msg))

    def register_subscriber(self, callback):
        logging.info("new subscriber arrived, sending the backlog")
        updates = items_to_updates(self.backlog.values())
        callback(json.dumps(updates))
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
        if not prologin.timeauth.check_token(
            self.get_argument('hmac'),
            self.application.sub_secret,
        ):
            self.send_error(403)
        else:
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
        msg = self.get_argument('msg')

        if not prologin.timeauth.check_token(
            self.get_argument('hmac'),
            self.application.pub_secret,
            msg
        ):
            logging.error('received an update request with invalid token')
            self.send_error(403)
            return

        self.application.pubsub_queue.post_message(json.loads(msg))


class Server(tornado.web.Application):
    """Synchronisation server. Users must derive from this class and implement
    required methods.
    """

    def __init__(self, pk, pub_secret, sub_secret, port):
        """The `shared_secret` is used to restrict clients that can add
        updates.
        """
        super(Server, self).__init__([
            (r'/poll', PollHandler),
            (r'/update', UpdateHandler),
        ])
        self.pk = pk
        self.port = port
        self.pub_secret = pub_secret.encode('utf-8')
        self.sub_secret = sub_secret.encode('utf-8')
        while True:
            try:
                backlog = self.get_initial_backlog()
                break
            except Exception:
                logging.exception('unable to get the backlog, retrying in 2s')
                time.sleep(2)
        self.pubsub_queue = InternalPubSubQueue(pk, backlog)

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
    """Synchronisation client."""

    def __init__(self, url, pk, pub_secret=None, sub_secret=None):
        self.url = url
        self.pk = pk
        self.pub_secret = pub_secret and pub_secret.encode('utf-8')
        self.sub_secret = sub_secret.encode('utf-8')

    def send_update(self, update):
        self.send_updates([update])

    def send_updates(self, updates):
        if self.pub_secret is None:
            raise ValueError("No secret provided, can't send update")

        msg = json.dumps(updates)
        r = requests.post(
            urllib.parse.urljoin(self.url, '/update'),
            data={
                'msg': msg,
                'hmac': prologin.timeauth.generate_token(self.pub_secret, msg),
            }
        )
        if r.status_code != 200:
            raise RuntimeError("Unable to post an update")

    def poll_updates(self, callback):
        if self.pk is None:
            raise ValueError('No primary key field name specified')
        if self.sub_secret is None:
            raise ValueError('No subscriber shared secret specified')

        while True:
            state = {}  # indexed by mac
            params = urllib.parse.urlencode({
                'hmac': prologin.timeauth.generate_token(self.sub_secret)
            })
            poll_url = urllib.parse.urljoin(self.url, '/poll?%s' % params)
            try:
                with urllib.request.urlopen(poll_url) as resp:
                    while True:
                        try:
                            l = resp.readline().decode('utf-8').strip()
                            updates = json.loads(l)
                        except Exception:
                            logging.exception('could not decode updates')
                            break
                        update_backlog(self.pk, state, updates)
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
