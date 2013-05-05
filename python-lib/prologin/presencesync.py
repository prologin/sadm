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

"""Client library for the PresenceSync service. Provides a simple callback
based API for sync clients, a login request function and a heartbeat function.

The sync clients use Tornado for async long polling.
"""

import logging
import prologin.config
import prologin.synchronisation
import urllib.parse

SUB_CFG = prologin.config.load('presencesync-sub')
PUB_CFG = prologin.config.load('presencesync-pub')


class Client(prologin.synchronisation.Client):

    ERROR_LOGGED_SOMEWHERE = 'already logged somewhere'
    ERROR_UNKNOWN = 'error unknown'

    def request_login(self, login, hostname):
        """Try to register `login` as logged on `hostname` to the PresenceSync
        server. Return None if login is accepted, or some ERROR_* constant
        otherwise.
        """
        r = self.send_request(
            '/login', self.pub_secret,
            {'login': login, 'hostname': hostname}
        )
        if r.status_code == 423:
            return self.ERROR_LOGGED_SOMEWHERE
        elif r.status_code != 200:
            return self.ERROR_UNKNOWN

    def send_heartbeat(self, login, hostname):
        """Send a heartbeat to the PresenceSync server in order to keep
        the `login` of the user logged on `hostname`.
        """
        # Just ignore the answer.
        self.send_request(
            '/heartbeat', self.pub_secret,
            {'login': login, 'hostname': hostname}
        )

    def remove_expired(self):
        """Remove expired logins."""
        # Just ignore the answer.
        self.send_request(
            '/remove_expired', self.pub_secret,
            {}
        )


def connect(pub=False):
    if pub:
        pub_secret = prologin.config.load('presencesync-pub')['shared_secret']
    else:
        pub_secret = None
    url = SUB_CFG['url']
    sub_secret = SUB_CFG['shared_secret']
    logging.info('Creating PresenceSync connection object: url=%s, can_pub=%s'
                 % (url, pub_secret is not None))
    return Client(
        url, 'login', pub_secret, sub_secret
    )
