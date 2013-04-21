# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Pierre Bourdon <pierre.bourdon@prologin.org>
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

"""Client library for the MDBSync service. Provides a simple callback based API
for sync clients, and exposes a function to send an update to a MDBSync server,
which will get redistributed to all listeners.

The sync clients use Tornado for async long polling.
"""

import hashlib
import hmac
import json
import logging
import prologin.config
import requests
import time
import urllib.parse
import urllib.request

CFG = prologin.config.load('mdbsync-sub')


class _MDBSyncClient:
    """Internal MDBSync client class. Use mdbsync.connect() to create a MDBSync
    client object.
    """

    def __init__(self, url, secret):
        self.url = url
        self.secret = secret

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
            raise RuntimeError("Unable to post update to MDBSync")

    def poll_updates(self, callback):
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
                                state[data['mac']] = data
                            elif update['type'] == 'delete':
                                if not data['mac'] in state:
                                    logging.error('removing unexisting data')
                                else:
                                    del state[data['mac']]
                        try:
                            callback(state.values())
                        except Exception:
                            logging.exception('error in the mdbsync callback')
            except Exception:
                logging.error('mdbsync connection lost, retrying in 2s')
                time.sleep(2)


def connect(pub=False):
    if pub:
        secret = prologin.config.load('mdbsync-pub')['shared_secret']
    else:
        secret = None
    url = CFG['url']
    logging.info('Creating MDBSync connection object: url=%s, has_secret=%s'
                 % (url, secret is not None))
    return _MDBSyncClient(url, secret)
