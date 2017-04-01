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
import prologin.tornadauth
import prologin.web
import prologin.webapi
import time
import tornado.ioloop
import tornado.web
import urllib.parse
import urllib.request
import sys


def apply_updates(pk, backlog, updates, watch=None):
    """Update `backlog` with `updates` using `pk` as primary key for records.

    Return metadata about what have been updated using an encoding like:
        {'obj1': 'updated', 'obj3': 'deleted', 'obj6': 'created'}
    The previous example means: the entity whose primary key is 'obj1' have
    been updated, 'obj6' have been created, ... Note that deletion and creation
    of entities *always* result in returned metadata, whatever `watch`
    contains.

    If `watch` is not None, it must be a set of field names. In this case,
    returned metadata includes only entities whose changes target fields in
    `watch`.

    For instance:
    >>> apply_updates('k', {1: {'k': 1, 'v': 2}},
                      [{'type': 'update', 'data': {'k': 1, 'v': 3}}])
    {1: 'updated'}
    >>> apply_updates('k', {
                          1: {'k': 1, 'v': 2, 'w': 1},
                          2: {'k': 2, 'v': 3, 'w': 4}
                      },
                      [
                          {'type': 'update', 'data': {'k': 1, 'v': 5, 'w': 6}}
                          {'type': 'update', 'data': {'k': 1, 'v': 7, 'w': 4}}
                      ],
                      watch={'w'})
    {1: 'updated'}
    """
    updates_metadata = {}

    for update in updates:

        data = update['data']
        key = data[pk]

        if update['type'] == 'update':
            # Add key to watched updates if any watched field changes.
            try:
                old_data = backlog[key]
            except KeyError:
                # The update must be watched if it creates a new record.
                updates_metadata[key] = 'created'
            else:
                # The update must be watched if all fields are updates or if at
                # least one watched field has changed.
                if watch is None or any(
                    data[field] != old_data[field] for field in watch
                ):
                    updates_metadata[key] = 'updated'

            backlog[key] = data

        elif update['type'] == 'delete':
            if backlog.pop(key, None) is None:
                logging.error('removing unexisting data')
            else:
                # All deletions are watched.
                updates_metadata[key] = 'deleted'

        else:
            logging.error('invalid update type: {}'.format(update['type']))

    return updates_metadata

def items_to_updates(items):
    return [
        {'type': 'update', 'data': item}
        for item in items
    ]


class BasePubSubQueue:
    """Maintain a backlog of updates. Used by the server.

    This is a base abstract class. It define common utilities, let
    subclasses implement required methods and let them add other methods.
    """
    def __init__(self):
        self.subscribers = set()

    def get_backlog_message(self):
        """Return the backlog that is sent to new subscribers as a JSON object.
        """
        raise NotImplementedError()

    def post_updates(self, update_msg):
        """Publish an update message to all subscribers."""
        logging.info('sending update message: %s' % update_msg)
        for callback in self.subscribers:
            callback(json.dumps(update_msg))

    def register_subscriber(self, callback):
        """Register a new subscriber to the queue.  `callback` will be invoked
        for each published update message (including the initial backlog).
        """
        logging.info('new subscriber arrived, sending the backlog')
        callback(json.dumps(self.get_backlog_message()))
        self.subscribers.add(callback)
        logging.info('added a new subscriber, count is now %d'
                         % len(self.subscribers))

    def unregister_subscriber(self, callback):
        """Remove a subscriber from the queue."""
        self.subscribers.remove(callback)
        logging.info('removed a subscriber, count is now %d'
                         % len(self.subscribers))

class DefaultPubSubQueue(BasePubSubQueue):
    """Maintain a backlog of updates for records with a field that is unique.
    """

    def __init__(self, pk, initial_backlog):
        super(DefaultPubSubQueue, self).__init__()
        self.pk = pk
        self.backlog = {}
        self.apply_updates(items_to_updates(initial_backlog))

    def get_backlog_message(self):
        return items_to_updates(self.backlog.values())

    #
    # Public interface
    #

    def apply_updates(self, updates):
        """Apply `updates` to the backlog and publish the corresponding update
        message.
        """
        apply_updates(self.pk, self.backlog, updates)
        self.post_updates(updates)


class PollHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @prologin.tornadauth.signature_checked('sub_secret')
    def get(self, msg):
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
    @prologin.tornadauth.signature_checked('pub_secret', check_msg=True)
    def post(self, msg):
        self.application.pubsub_queue.apply_updates(json.loads(msg))


class Server(prologin.web.TornadoApp):
    """Synchronisation server. Users must derive from this class and implement
    required methods.
    """

    def __init__(self, pk, pub_secret, sub_secret, port, app_name):
        """The `shared_secret` is used to restrict clients that can add
        updates.
        """
        super().__init__(self.get_handlers(), app_name)
        self.pk = pk
        self.port = port
        self.pub_secret = pub_secret.encode('utf-8')
        self.sub_secret = sub_secret.encode('utf-8')
        self.pubsub_queue = self.create_pubsub_queue()

    def start(self):
        """Run the server."""
        self.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()

    def get_handlers(self):
        """Return a list of URL/request handlers couples for this server."""
        return [
            (r'/poll', PollHandler),
            (r'/update', UpdateHandler),
        ]

    def create_pubsub_queue(self):
        """Create and return a brand new pubsub queue, taking care of filling
        it with an initial backlog.

        Override this method if you want to have a custom pubsub queue.
        """

        while True:
            try:
                backlog = self.get_initial_backlog()
                break
            except Exception as e:
                logging.exception(
                    'unable to get the backlog, retrying in 2s: {}: {}'.format(
                        type(e).__name__, e
                    )
                )
                time.sleep(2)
        return DefaultPubSubQueue(self.pk, backlog)

    def get_initial_backlog(self):
        """Return the initial state of updates as a list.

        Users must give an implementation for this method.
        """
        raise NotImplementedError()


class Client(prologin.webapi.Client):
    """Synchronisation client."""

    def __init__(self, url, pk, pub_secret=None, sub_secret=None):
        super(Client, self).__init__(url)
        self.pk = pk
        self.pub_secret = pub_secret and pub_secret.encode('utf-8')
        self.sub_secret = sub_secret.encode('utf-8')

    def send_update(self, update):
        self.send_updates([update])

    def send_updates(self, updates):
        if self.pub_secret is None:
            raise ValueError("No secret provided, can't send update")

        r = self.send_request('/update', self.pub_secret, updates)
        if r.status_code != 200:
            raise RuntimeError("Unable to post an update")

    def poll_updates(self, callback, watch=None):
        """Call `callback` for each set of updates.

        `callback` is called with an iterable that contain an up-to-date
        mapping of records (primary_key -> record), and with a mapping: primary
        key changed -> kind of update, for all records than has watched
        changes. Note that the callback is invoked even if the watched list of
        changes is empty. See `updated_backlog` for the meaning of `watch` and
        for returned watched changes.
        """

        if self.pk is None:
            raise ValueError('No primary key field name specified')
        if self.sub_secret is None:
            raise ValueError('No subscriber shared secret specified')

        while True:
            params = urllib.parse.urlencode({
                'data': '{}',
                'hmac': prologin.timeauth.generate_token(self.sub_secret),
            })
            poll_url = urllib.parse.urljoin(self.url, '/poll?%s' % params)
            try:
                with urllib.request.urlopen(poll_url) as resp:
                    state = {}  # indexed by self.pk
                    while True:
                        try:
                            l = resp.readline().decode('utf-8').strip()
                            updates = json.loads(l)
                        except Exception:
                            logging.exception('could not decode updates')
                            break
                        updates_metadata = apply_updates(
                            self.pk, state,
                            updates, watch
                        )
                        try:
                            callback(state, updates_metadata)
                        except Exception as e:
                            logging.exception(
                                'error in the synchorisation client '
                                'callback: %s' % e
                            )
            except Exception as e:
                logging.exception('connection lost to synchronisation server:'
                                  ' %s (url: %s)' % (e, poll_url))
                sys.exit(1)
