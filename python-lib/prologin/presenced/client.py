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

"""Presenced client library: provide a function to request a login."""

import logging
import prologin.config
import prologin.webapi
import pwd


def is_prologin_uid(uid):
    """Return if `uid` belongs to a user handled by Prologin."""
    return 10000 <= uid < 20000


def is_prologin_user(user):
    """Return if `user` (a username or an UID) is handled by Prologin.

    Raise a KeyError if the user does not exist."""
    if isinstance(user, str):
        uid = pwd.getpwnam(user).pw_uid
    else:
        uid = pwd.getpwuid(user).pw_uid
    return is_prologin_uid(uid)


class Client(prologin.webapi.Client):
    def __init__(self, url, secret):
        super(Client, self).__init__(url)
        self.secret = secret.encode('ascii')

    def send_heartbeat(self):
        self.send_request('/send_heartbeat', self.secret, {})

    def request_login(self, login):
        """Return None if login is accepted, a reason if not."""
        r = self.send_request('/login', self.secret, {'login': login})
        logging.debug('Request login status code: %s', r.status_code)
        if r.status_code != 200:
            return r.text or 'No reason given'
        else:
            return None


def connect():
    CFG = prologin.config.load('presenced-client')
    url = CFG['url']
    secret = CFG['shared_secret']
    logging.info('Creating Presenced client connection object: url=%s', url)
    return Client(url, secret)
