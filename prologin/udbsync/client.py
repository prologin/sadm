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

"""Client library for the UDBSync service. Provides a simple callback based API
for sync clients, and exposes a function to send an update to a UDBSync server,
which will get redistributed to all listeners.

The sync clients use Tornado for async long polling.
"""

import logging

import prologin.config
import prologin.synchronisation

SUB_CFG = prologin.config.load('udbsync-sub')


def _connect_args(publish):
    if publish:
        pub_secret = prologin.config.load('udbsync-pub')['shared_secret']
    else:
        pub_secret = None
    url = SUB_CFG['url']
    sub_secret = SUB_CFG['shared_secret']
    logging.info(
        'Creating UDBSync connection object: url=%s, publish=%s',
        url,
        pub_secret is not None,
    )
    return url, 'login', pub_secret, sub_secret


def connect(publish=False):
    return prologin.synchronisation.Client(*_connect_args(publish))


def aio_connect(publish=False):
    return prologin.synchronisation.AsyncClient(*_connect_args(publish))
