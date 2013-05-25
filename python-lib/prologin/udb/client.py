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

"""Client library for the User Database (UDB)."""

import json
import logging
import prologin.config
import prologin.timeauth
import requests
import urllib.parse

CFG = prologin.config.load('udb-client')


class RegistrationError(Exception):
    def __init__(self, message):
        super(RegistrationError, self).__init__()
        self.message = message


class _UDBClient:
    """Internal UDB client class. Use udb.connect() to create an UDB client
    object.
    """

    def __init__(self, url, secret=None):
        self.url = url
        self.secret = secret and secret.encode('utf-8')

    def _submit_rpc(self, path, data=None):
        """Sends a RPC to the udb. Passes authentication data if available.

        Args:
          path: Server path of the RPC (from self.url).
          data: Optional data dictionary to POST.
        """
        url = urllib.parse.urljoin(self.url, path)
        if self.secret:
            data['hmac'] = prologin.timeauth.generate_token(self.secret)
        params = { 'data': data }
        r = requests.post(url, **params)
        return r.json()

    def query(self, **kwargs):
        """Query the UDB using the Django query syntax. The possible fields
        are:
          login, realname: login and civil name of the user
          uid : its system UID
          group: kind of user, either user/orga/root
          shell: its default system shell
          ssh_key: SSH public key of the user
        """
        fields = {
            'login', 'uid', 'group', 'shell', 'ssh_key'
        }
        for q in kwargs:
            base = q.split('_')[0]
            if base not in fields:
                raise ValueError('%r is not a valid query argument' % q)
        try:
            post_data = json.dumps(kwargs)
        except TypeError:
            raise ValueError('non serializable argument type')
        return self._submit_rpc('/query', data=kwargs)


def connect(auth=False):
    if auth:
        secret = prologin.config.load('udb-client-auth')['shared_secret']
    else:
        secret = None
    url = CFG['url']
    logging.info('Creating UDB connection object: url=%s, has_secret=%s'
                 % (url, secret is not None))
    return _UDBClient(url, secret)
