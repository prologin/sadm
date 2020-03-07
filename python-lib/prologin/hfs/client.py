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

"""Client library for Home Filesystems (HFS)."""

import json
import logging

import prologin.config
import prologin.mdb.client
import prologin.udb.client
import prologin.webapi

CFG = prologin.config.load('hfs-client')


class Client(prologin.webapi.Client):
    """Internal HFS client. Use hfs.connect() to create a HFS client object."""

    def __init__(self, url_pattern, host_pattern, secret):
        super(Client, self).__init__(None)
        self.url_pattern = url_pattern
        self.host_pattern = host_pattern
        self.secret = secret.encode('ascii')

    def _log_and_raise(self, msg, exn=RuntimeError):
        logging.error(msg)
        raise exn(msg)

    def get_hfs(self, login, hostname):
        """Request a HFS for `login` which is logged on `hostname`.

        Return HFS server: (hfs_hostname, hfs_port).
        """

        logging.info(
            'Requesting a HFS for user %s on host %s...', login, hostname
        )

        match = prologin.udb.client.connect().query(login=login)
        if len(match) != 1:
            self._log_and_raise('No such user: {}'.format(login))
        user = match[0]
        match = prologin.mdb.client.connect().query(hostname=hostname)
        if len(match) != 1:
            self._log_and_raise('No such machine: {}'.format(hostname))
        machine = match[0]

        utype = user['group']
        hfs_id = machine['hfs']
        hfs_host = self.host_pattern.format(hfs_id)
        hfs_url = self.url_pattern.format(hfs_host)
        logging.info(
            'Requesting a HFS on %s for user %s on host %s...',
            hfs_host,
            login,
            hostname,
        )

        r = self.send_request(
            '/get_hfs',
            self.secret,
            {'user': login, 'hfs': hfs_id, 'utype': utype},
            url=hfs_url,
        )
        if r.status_code != 200:
            self._log_and_raise('Cannot get a HFS: {}'.format(r.text))
        else:
            info = json.loads(r.text)

        logging.info(
            'Got a HFS for user %s on host %s: %s:%s',
            login,
            hostname,
            hfs_host,
            info['port'],
        )
        return (hfs_host, info['port'])


def connect():
    url_pattern = CFG['url_pattern']
    host_pattern = CFG['host_pattern']
    secret = CFG['shared_secret']
    logging.info(
        'Creating HFS connection object: host_pattern=%s', host_pattern
    )
    return Client(url_pattern, host_pattern, secret)
