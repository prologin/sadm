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

"""MDBSync client regenerating the DHCP configuration at each MDB update.
"""

import logging
import os
import prologin.log
import prologin.mdbsync.client


def update_dhcp_config(machines, metadata):
    logging.warning("Received update, regenerating DHCP config")
    fragments = []
    for m in machines.values():
        fragment = (
            'host %(hostname)s {\n'
            '\thardware ethernet %(mac)s;\n'
            '\tfixed-address %(ip)s;\n'
            '\toption host-name "%(hostname)s";\n'
            '}\n'
        )
        fragments.append(fragment % m)

    with open('/etc/dhcpd/generated.conf', 'w') as fp:
        fp.write('\n'.join(fragments))

    logging.warning("Reloading DHCP config")
    os.system('systemctl restart dhcpd4')

if __name__ == '__main__':
    prologin.log.setup_logging('mdbdhcp')
    prologin.mdbsync.client.connect().poll_updates(update_dhcp_config)
