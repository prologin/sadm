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

import json
import logging
import prologin.config
import prologin.synchronisation

SUB_CFG = prologin.config.load('presencesync-sub')


class Client(prologin.synchronisation.Client):
    def get_list(self):
        """Return a mapping: login -> hostname for all logged in users."""
        r = self.send_request('/get_list', self.sub_secret, {}, method='get')
        if r.status_code != 200:
            raise RuntimeError(
                'Cannot get the list of logged in users: {}'.format(r.text)
            )
        else:
            return json.loads(r.text)

    def request_login(self, login, hostname):
        """Try to register `login` as logged on `hostname` to the PresenceSync
        server. Return None if login is accepted, or some login failure reason
        otherwise.
        """
        r = self.send_request(
            '/login', self.pub_secret, {'login': login, 'hostname': hostname}
        )
        logging.debug(
            'Request login: PresenceSync status code is %s', r.status_code
        )
        if r.status_code != 200:
            return r.text or 'No reason given'
        else:
            return None

    def notify_logout(self, login, hostname):
        """Tell that `login` is logging out from `hostname` to the PresenceSync
        server. Return None if this is fine, or some failure reason otherwise.
        """
        r = self.send_request(
            '/logout', self.pub_secret, {'login': login, 'hostname': hostname}
        )
        logging.debug(
            'Notify logout: PresenceSync status code is %s', r.status_code
        )
        if r.status_code != 200:
            return r.text or 'No reason given'
        else:
            return None

    def send_heartbeat(self, login, hostname):
        """Send a heartbeat to the PresenceSync server in order to keep
        the `login` of the user logged on `hostname`.
        """
        # Just ignore the answer.
        self.send_request(
            '/heartbeat',
            self.pub_secret,
            {'login': login, 'hostname': hostname},
        )

    def remove_expired(self):
        """Remove expired logins."""
        # Just ignore the answer.
        self.send_request('/remove_expired', self.pub_secret, {})


class AsyncClient(prologin.synchronisation.AsyncClient):
    async def get_list(self):
        r = await self.send_request('/get_list', self.sub_secret, {}, 'get')
        return await r.json()

    async def request_login(self, login, hostname):
        r = await self.send_request(
            '/login', self.pub_secret, {'login': login, 'hostname': hostname}
        )
        logging.debug(
            "Request login: PresenceSync status code is %s", r.status
        )
        return (await r.text()) or "No reason given"

    async def send_heartbeat(self, login, hostname):
        await self.send_request(
            '/heartbeat',
            self.pub_secret,
            {'login': login, 'hostname': hostname},
        )

    async def remove_expired(self):
        await self.send_request('/remove_expired', self.pub_secret, {})


def _connect_args(publish):
    if publish:
        pub_secret = prologin.config.load('presencesync-pub')['shared_secret']
    else:
        pub_secret = None
    url = SUB_CFG['url']
    sub_secret = SUB_CFG['shared_secret']
    logging.info(
        "Creating PresenceSync connection object: url=%s, publish=%s",
        url,
        pub_secret is not None,
    )
    return url, 'login', pub_secret, sub_secret


def connect(publish=False):
    return Client(*_connect_args(publish))


def aio_connect(publish=False):
    return AsyncClient(*_connect_args(publish))
