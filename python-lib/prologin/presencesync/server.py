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

"""PresenceSync server: sends logged users changes to PresenceSync clients,
accept or deny connection requests from presencd daemons instances and mainain
a list of logged users, taking care of timeouts thanks to heartbeats.
"""

import collections
import json
import logging
import prologin.config
import prologin.log
import prologin.mdb.client
import prologin.presencesync.client
import prologin.synchronisation
import prologin.tornadauth
import prologin.udb.client
import sys
import threading
import time
import tornado.web

from .monitoring import (
    presencesync_login_failed,
    monitoring_start,
)

PUB_CFG = prologin.config.load('presencesync-pub')
SUB_CFG = prologin.config.load('presencesync-sub')

if 'shared_secret' not in PUB_CFG:
    raise RuntimeError(
        'Missing shared_secret in the presencesync-pub YAML config'
    )

if 'shared_secret' not in SUB_CFG:
    raise RuntimeError(
        'Missing shared_secret in the presencesync-sub YAML config'
    )


class TimeoutedPubSubQueue(prologin.synchronisation.BasePubSubQueue):
    """Maintain a backlog of logged in users per machine. Take care of
    information expiration.

    The internal backlog is a little bit exotic here: it's a mapping: user
    login -> (expiration timestamp, hostname).  Filtering out expired
    information has to be triggered externally: this class just provide a
    function to do it.
    """

    # Time before a new information is expired (in seconds).
    TIMEOUT = SUB_CFG['timeout']

    def __init__(self):
        super(TimeoutedPubSubQueue, self).__init__()
        self.start_ts = None
        # By default, a machine has no user and its information is expired.
        self.backlog = {}
        # Mapping hostname -> user login or None.
        self.reverse_backlog = collections.defaultdict(lambda: None)

        self.udb = prologin.udb.client.connect()
        self.mdb = prologin.mdb.client.connect()

    def item_to_update(self, update_type, login, hostname):
        return {
            'type': update_type,
            'data': {'login': login, 'hostname': hostname},
        }

    def remove_expired(self):
        """Remove expired users and return the set of removed logins."""
        current_ts = int(time.time())

        # First collect users to remove.
        to_remove = set()
        for login, (expiration_ts, hostname) in self.backlog.items():
            if expiration_ts <= current_ts:
                to_remove.add(login)

        # Then remove them and update the reverse backlog in the same time.
        for login in to_remove:
            _, hostname = self.backlog.pop(login, (None, None))
            self.reverse_backlog.pop(hostname, None)

        return to_remove

    def remove_and_publish_expired(self):
        """Remove expired users and publish updates for it if needed."""
        update_msg = [
            self.item_to_update('delete', login, None)
            for login in self.remove_expired()
        ]
        if update_msg:
            self.post_updates(update_msg)

    def update_backlog(self, login, hostname):
        """Register `login` as logged on `hostname`.  Send needed update
        messages.  Check for expired logins first.  Should be used only
        internally.
        """
        removed = self.remove_expired()

        current_ts = int(time.time())
        new_expiration_ts = current_ts + self.TIMEOUT

        # This update may be going to replace a previously logged in user on
        # `hostname`: see below.
        old_login = self.reverse_backlog[hostname]

        # Update backlogs.
        self.backlog[login] = (new_expiration_ts, hostname)
        self.reverse_backlog[hostname] = login
        # Do not "free" the previous hostname in the reverse backlog: if it is
        # still busy, it is not sync'ed anymore with PresencSync, and sessions
        # on it must be closed.
        # TODO: if self.reverse_backlog[hostname] not in (None, login), send a
        # message to admins!

        update_msg = []
        if old_login != login:
            if old_login:
                # Here, the previously logged in user will replaced: published
                # he logged off.
                removed.add(old_login)
            update_msg.append(self.item_to_update('update', login, hostname))

        # Prepend updates for logged off users.
        update_msg = [
            self.item_to_update('delete', login, None)
            for login in removed
        ] + update_msg

        if update_msg:
            self.post_updates(update_msg)

    def get_backlog_message(self):
        """Return an update message-formatted backlog.  Check for expired
        logins first.
        """
        self.remove_and_publish_expired()
        return [
            self.item_to_update('update', login, hostname)
            for login, (_, hostname) in self.backlog.items()
        ]

    def is_login_allowed(self, login, hostname):
        """Return None if `login` is allowed to log on `hostname`, or a reason
        message if not.
        """

        # A login request is accepted if and only if one of the following
        # conditions is True:

        def fail(reason):
            logging.debug(reason)
            return reason

        # 1 - The user is already logged on `hostname`
        if self.backlog.get(login, (None, None))[1] == hostname:
            labels = {'user': login, 'reason': 'already_logged'}
            presencesync_login_failed.labels(labels).inc()

            logging.debug('{} is already logged on {}'.format(login, hostname))
            return None

        # 2 - The user is not logged in anywhere, nobody is logged on
        #     `hostname` and the user is allowed to log on `hostname` (a
        #     contestant cannot log on an organizer host.
        if login in self.backlog:
            labels = {'user': login, 'reason': 'already_logged'}
            presencesync_login_failed.labels(labels).inc()

            return fail('{} is already logged somewhere else'.format(login))
        elif hostname in self.reverse_backlog:
            labels = {'user': login, 'reason': 'busy'}
            presencesync_login_failed.labels(labels).inc()

            return fail('{} is busy'.format(hostname))
        else:
            logging.debug(
                '{} is not logged anywhere and {} is not busy'.format(
                    login, hostname
                )
            )
            match = self.mdb.query(hostname=hostname)
            if len(match) != 1:
                # Either there is no such hostname: refuse it, either there are
                # many machine for a single hostname, which should never
                # happen, or we have a big problem!
                labels = {'user': login, 'reason': 'machine_not_registered'}
                presencesync_login_failed.labels(labels).inc()

                return fail('{} is not a registered machine'.format(hostname))
            machine = match[0]

            match = self.udb.query(login=login)
            if len(match) != 1:
                labels = {'user': login, 'reason': 'user_not_registered'}
                presencesync_login_failed.labels(labels).inc()

                return fail('{} is not a registered user'.format(login))
            user = match[0]

            # The login will fail only if a simple user (contestant) tries to
            # log on a machine not for contestants. :-)
            logging.debug('USER {} is a {}, MACHINE {} is a {}'.format(
                login, user['group'],
                hostname, machine['mtype']
            ))
            if user['group'] == 'user' and machine['mtype'] != 'user':
                labels = {'user': login, 'reason': 'user_not_allowed'}
                presencesync_login_failed.labels(labels).inc()

                return fail(
                    '{} is not a kind of user'
                    ' that is allowed to log on {}'.format(login, hostname)
                )

            return None

        # By default, refuse the login.
        labels = {'user': login, 'reason': 'default'}
        presencesync_login_failed.labels(labels).inc()

        return fail('Default for {} on {}: refuse'.format(login, hostname))

    #
    # Public interface
    #

    def start(self):
        self.start_ts = int(time.time())

    def get_list(self):
        """Return a mapping: login -> hostname for all logged in users.  Check
        for expired logins first.
        """
        self.remove_and_publish_expired()
        return {
            login: info[1]
            for login, info in self.backlog.items()
        }

    def request_login(self, login, hostname):
        """Try to register `login` as logged on `hostname`.  Return None if
        successful, and if it is, send an update for it.  Return a failure
        reason otherwise.  Also check for expired logins first.
        """
        self.remove_and_publish_expired()

        # Refuse all requests until the server is started for at least the
        # expiration TIMEOUT. This will prevent users from logging until
        # database is regenerated thanks to heartbeats.
        if self.start_ts is None or time.time() < self.start_ts + self.TIMEOUT:
            logging.debug('Login for {} on {} refused: too early'.format(
                login, hostname
            ))
            if self.start_ts is None:
                logging.debug('Starting date is undefined')
            else:
                logging.debug('Still have to wait for {} seconds'.format(
                    int(self.start_ts + self.TIMEOUT - time.time())
                ))
            labels = {'user': login, 'reason': 'too_early'}
            presencesync_login_failed.labels(labels).inc()
            return 'Too early login: try again later'

        failure_reason = self.is_login_allowed(login, hostname)
        if failure_reason:
            return failure_reason
        else:
            self.update_backlog(login, hostname)
            return None

    def update_with_heartbeat(self, login, hostname):
        """Accept and register as-is the association between `login` and
        `hostname`, sending an update message if needed.  Check for expired
        logins first.
        """
        self.remove_and_publish_expired(self)
        self.update_backlog(login, hostname)


class GetListHandler(tornado.web.RequestHandler):
    @prologin.tornadauth.signature_checked('sub_secret', check_msg=True)
    def get(self, msg):
        self.write(json.dumps(
            self.application.pubsub_queue.get_list()
        ))


class LoginHandler(tornado.web.RequestHandler):
    @prologin.tornadauth.signature_checked('pub_secret', check_msg=True)
    def post(self, msg):
        msg = json.loads(msg)
        failure_reason = self.application.pubsub_queue.request_login(
            msg['login'], msg['hostname']
        )
        if failure_reason:
            self.set_status(423, 'Login refused')
            self.write(failure_reason)
        else:
            self.set_status(200, 'OK')


class HeartbeatHandler(tornado.web.RequestHandler):
    @prologin.tornadauth.signature_checked('pub_secret', check_msg=True)
    def post(self, msg):
        msg = json.loads(msg)
        self.application.pubsub_queue.update_backlog(
            msg['login'], msg['hostname']
        )
        self.set_status(200, 'OK')


class RemoveExpiredHandler(tornado.web.RequestHandler):
    @prologin.tornadauth.signature_checked('pub_secret', check_msg=True)
    def post(self, msg):
        self.application.pubsub_queue.remove_and_publish_expired()
        self.set_status(200, 'OK')


class SyncServer(prologin.synchronisation.Server):
    def __init__(self, pub_secret, sub_secret, port):
        super(SyncServer, self).__init__(
            'login', pub_secret, sub_secret, port, 'presencesync'
        )
        self.start_ts = None

    def start(self):
        self.pubsub_queue.start()
        self.removing_expired_thread = threading.Thread(
            target=self.loop_removing_expired,
            daemon=True
        )
        self.removing_expired_thread.start()
        super(SyncServer, self).start()

    def loop_removing_expired(self):
        """Loop forever, asking the PrecenceSync server to remove expired
        logins periodically.
        """
        conn = prologin.presencesync.client.connect(pub=True)
        while True:
            # Communicate with the PresenceSync server just like any other
            # client in order to handle concurrent accesses nicely.

            # Try to send a message, forever and ever and ever.
            try:
                conn.remove_expired()
            except Exception as e:
                logging.exception(
                    'Expired removing thread: error while sending a message to'
                    ' the PresenceSync server, retrying in 2s'
                )
                time.sleep(2)
            else:
                time.sleep(TimeoutedPubSubQueue.TIMEOUT / 2)

    def get_handlers(self):
        # Override default handlers: direct updating is not allowed.
        return [
            (r'/poll', prologin.synchronisation.PollHandler),
            (r'/get_list', GetListHandler),
            (r'/login', LoginHandler),
            (r'/heartbeat', HeartbeatHandler),
            (r'/remove_expired', RemoveExpiredHandler),
        ]

    def create_pubsub_queue(self):
        """Initially, no user is logged. Heartbeats are trusted, so we can
        rebuild the state with them."""
        return TimeoutedPubSubQueue()


if __name__ == '__main__':
    prologin.log.setup_logging('presencesync')
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000

    monitoring_start()

    server = SyncServer(
        PUB_CFG['shared_secret'],
        SUB_CFG['shared_secret'],
        port
    )
    server.start()
