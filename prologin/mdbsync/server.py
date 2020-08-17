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

"""MDBSync server: sends MDB changes to MDBSync clients.
"""

import prologin.config
import prologin.log
import prologin.mdb.client
import prologin.synchronisation
import sys


PUB_CFG = prologin.config.load('mdbsync-pub')
SUB_CFG = prologin.config.load('mdbsync-sub')


class SyncServer(prologin.synchronisation.Server):
    def __init__(self, pub_secret, sub_secret, port):
        super().__init__('mac', pub_secret, sub_secret, port, 'mdbsync')

    def get_initial_backlog(self):
        return prologin.mdb.client.connect().query()


if __name__ == '__main__':
    prologin.log.setup_logging('mdbsync')

    if 'shared_secret' not in PUB_CFG:
        raise RuntimeError(
            "Missing shared_secret in the mdbsync-pub YAML config"
        )

    if 'shared_secret' not in SUB_CFG:
        raise RuntimeError(
            "Missing shared_secret in the mdbsync-sub YAML config"
        )

    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    server = SyncServer(
        PUB_CFG['shared_secret'], SUB_CFG['shared_secret'], port
    )
    server.start()
