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

import logging
import prologin.config
import prologin.rpc.client

CFG = prologin.config.load('udb-client')


def connect(auth=False):
    if auth:
        secret = prologin.config.load('udb-client-auth')['shared_secret']
        secret = secret.encode()
    else:
        secret = None
    url = CFG['url']
    logging.info('Creating UDB connection object: url=%s, has_secret=%s'
                 % (url, secret is not None))
    return prologin.rpc.client.SyncClient(CFG['url'], secret=secret)
