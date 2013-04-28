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

"""UDBSync server: sends UDB changes to UDBSync clients.
"""

import prologin.config
import prologin.log
import prologin.udb
import prologin.synchronisation
import sys


CFG = prologin.config.load('udbsync-pub')

if 'shared_secret' not in CFG:
    raise RuntimeError("Missing shared_secret in the YAML config")


class SyncServer(prologin.synchronisation.Server):

    def get_initial_backlog(self):
        users = prologin.udb.connect().query()
        return [{ "type": "update", "data": u } for u in users]


if __name__ == '__main__':
    prologin.log.setup_logging('udbsync')
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    server = SyncServer(CFG['shared_secret'], port)
    server.start()
