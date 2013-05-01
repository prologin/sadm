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
import prologin.presencesync
import prologin.synchronisation
import sys
import threading
import time


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
        # By default, a machine has no user and its information is expired.
        self.backlog = collections.defaultdict(lambda: (0, None))
        # Mapping hostname -> user login or None.
        self.reverse_backlog = collections.defaultdict(lambda: None)

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

    def get_backlog(self):
        """Return an update message-formatted backlog.  Check for expired
        logins first.
        """
        self.remove_and_publish_expired()
        return [
            self.item_to_update('update', login, hostname)
            for login, (_, hostname) in self.backlog.items()
        ]

    #
    # Public interface
    #

    def request_login(self, login, hostname):
        """Try to register `login` as logged on `hostname`.  Return if
        successful, and if it is, send an update for it.  Check for expired
        logins first.
        """
        self.remove_and_publish_expired()

        # A login request is accepted if and only if one of the following
        # conditions is True:
        # 1 - The user is not logged in anywhere and nobody is loggen on
        #     `hostname`
        # 2 - The user is already loggen on `hostname`
        if (
            (
                login not in self.backlog
                and hostname not in self.reverse_backlog
            )
            or self.backlog[login][1] == hostname
        ):
            self.update_backlog(login, hostname)
            return True
        else:
            return False

    def update_with_heartbeat(self, login, hostname):
        """Accept and register as-is the association between `login` and
        `hostname`, sending an update message if needed.  Check for expired
        logins first.
        """
        self.remove_and_publish_expired(self)
        self.update_backlog(login, hostname)


class LoginHandler(prologin.synchronisation.AuthRequestHandler):
    def post(self):
        try:
            msg = self.check_authentication(self.application.pub_secret, True)
        except RuntimeError:
            pass
        else:
            msg = json.loads(msg)
            if self.pubsub_queue.request_login(msg['login'], msg['hostname']):
                self.set_status(200, 'OK')
            else:
                self.set_status(423, 'User already logged somewhere else')


class HeartbeatHandler(prologin.synchronisation.AuthRequestHandler):
    def post(self):
        try:
            msg = self.check_authentication(self.application.pub_secret, True)
        except RuntimeError:
            pass
        else:
            msg = json.loads(msg)
            self.pubsub_queue.update_host(msg['login'], msg['hostname'])
            self.set_status(200, 'OK')


class RemoveExpiredHandler(prologin.synchronisation.AuthRequestHandler):
    def post(self):
        try:
            msg = self.check_authentication(self.application.pub_secret, True)
        except RuntimeError:
            pass
        else:
            self.pubsub_queue.remove_and_publish_expired()
            self.set_status(200, 'OK')


class SyncServer(prologin.synchronisation.Server):
    def __init__(self, pub_secret, sub_secret, port):
        super(SyncServer, self).__init__(
            'login', pub_secret, sub_secret, port
        )
        self.start_ts = None

    def start(self):
        self.start_ts = int(time.time())
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
        conn = None
        while True:
            # Communicate with the PResenceSync server just like any other
            # client in order to handle concurrent accesses nicely.

            # Try to connect, forever and ever and ever.
            while not conn:
                try:
                    conn = prologin.presencesync.connect(pub=True)
                except Exception as e:
                    logging.exception(
                        'Expired removing thread: error while connecting to'
                        ' the PresenceSync server, retrying in 2s'
                    )
                    time.sleep(2)
            try:
                conn.remove_expired()
            except Exception as e:
                conn = None
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
            (r'/login', LoginHandler),
            (r'/heartbeat', HeartbeatHandler),
            (r'/remove_expired', RemoveExpiredHandler),
        ]

    def create_pubsub_queue(self):
        """Initially, no user is logged. Heartbeats are trusted, so we can
        rebuild the state with them."""
        return TimeoutedPubSubQueue()


if __name__ == '__main__':
    prologin.log.setup_logging('presencesync', verbose=True, local=True)
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    server = SyncServer(
        PUB_CFG['shared_secret'],
        SUB_CFG['shared_secret'],
        port
    )
    server.start()
