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


def update_backlog(pk, backlog, updates, watch=None):
    """Update `backlog` with `updates` using `pk` as primary key for records.
    If `watch` is None, the set of primary keys for updated records is
    returned. Otherwise, `watch` must be a set of fields, and the set of
    primary keys for records whose changed fields match those is returned.

    For instance:
    >>> update_backlog('k', {'k': 1, {'k': 1, 'v': 2}},
                       [{'type': 'update', 'data': {'k': 1, 'v': 3}}])
    {1}
    >>> update_backlog('k', {'k': 1, {'k': 1, 'v': 2, 'w': 1}},
                       [{'type': 'update', 'data': {'k': 1, 'v': 3, 'w': 1}}],
                       watch={'w'})
    set()
    """
    watched_updates = set()

    for update in updates:

        data = update['data']
        key = data[pk]

        if update['type'] == 'update':
            # Add key to watched updates if any watched field changes.
            try:
                old_data = backlog[key]
            except KeyError:
                # The update must be watched if it creates a new record.
                watched_updates.add(key)
            else:
                # The update must be watched if all fields are updates or if at
                # least one watched field has changed.
                if watch is None or any(
                    data[field] != old_data[field] for field in watch
                ):
                    watched_updates.add(key)

            backlog[key] = data

        elif update['type'] == 'delete':
            if backlog.pop(key, None) is None:
                logging.error('removing unexisting data')
            else:
                # All deletions are watched.
                watched_updates.add(key)

        else:
            logging.error('invalid update type: {}'.format(update['type']))

    return watched_updates

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


class AuthRequestHandler(tornado.web.RequestHandler):
    """Regular base handler class, just add a few utility to check auth."""

    def check_authentication(self, secret, check_msg=False):
        """Return the message if the current request is correctly authenticated
        with respects to `secret` (checking the message itself if asked to).
        Send an error response and raise a RuntimeError otherwise.
        """

        msg = (
            self.get_argument('msg')
            if check_msg else
            None
        )
        if not prologin.timeauth.check_token(
            self.get_argument('hmac'), secret, msg
        ):
            logging.error('received an update request with invalid token')
            self.send_error(403)
            raise RuntimeError('Invalid token')
        else:
            return self.get_argument('msg', None)


class PollHandler(AuthRequestHandler):
    @tornado.web.asynchronous
    def get(self):
        try:
            msg = self.check_authentication(self.application.sub_secret)
        except RuntimeError:
            pass
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


class UpdateHandler(AuthRequestHandler):
    def post(self):
        try:
            msg = self.check_authentication(self.application.pub_secret, True)
        except RuntimeError:
            pass
        else:
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

    def send_request(self, resource, secret, data):
        """Send an request that is authenticated using `secret` and that
        contains `data` (a JSON data structure) to `resource`. Return the
        request object.
        """
        msg = json.dumps(data)
        return requests.post(
            urllib.parse.urljoin(self.url, resource),
            data={
                'msg': msg,
                'hmac': prologin.timeauth.generate_token(secret, msg),
            }
        )

    def send_update(self, update):
        self.send_updates([update])

    def send_updates(self, updates):
        if self.pub_secret is None:
            raise ValueError("No secret provided, can't send update")

        msg = json.dumps(updates)
        r = self.send_request('/update', self.pub_secret, updates)
        if r.status_code != 200:
            raise RuntimeError("Unable to post an update")

    def poll_updates(self, callback, watch=None):
        """Call `callback` for each set of updates.

        `callback` is called with an iterable that contain an up-to-date list
        of records, and with the set of key for records than has watched
        changes. Note that the callback is invoked even if the watched list of
        changes is empty. See `updated_backlog` for the meaning of `watch` and
        for returned watched changes.
        """

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
                        watched_updates = update_backlog(
                            self.pk, state,
                            updates, watch
                        )
                        try:
                            callback(state.values(), watched_updates)
                        except Exception:
                            logging.exception(
                                'error in the synchorisation client callback'
                            )
            except Exception:
                logging.error(
                    'connection lost to synchronisation server, retrying in 2s'
                )
                time.sleep(2)
