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

"""MDBSync client regenerating the DNS configuration at each MDB update.
"""

import logging
import os.path
import prologin.log
import prologin.mdbsync


def build_zone(name, records):
    logging.info('Building zone file for %r' % name)
    path = os.path.join('/etc/named', 'generated_%s.zone' % name)
    if not os.path.exists(path):
        serial = 1
    else:
        # Find the current serial. It is on a line formatted like this:
        # \t\t\t1 ; @@SERIAL@@
        with open(path) as fp:
            text = fp.read()
            comment_pos = text.index('@@SERIAL@@')
            serial_pos = text.rindex('\t', 0, comment_pos) + 1
            serial_end_pos = text.index(' ', serial_pos, comment_pos)
            serial = int(text[serial_pos:serial_end_pos]) + 1

    ZONE_HEADER = (
        '; THIS IS A GENERATED FILE\n'
        '; Do not modify it manually - see mdbdns.py\n'
        '$TTL\t10\n'
        '@\tIN\tSOA\tns.prolo.\thostmaster.ns.prolo.\t(\n'
        '\t\t\t%(serial)s ; @@SERIAL@@\n'
        '\t\t\t1200 ; Refresh\n'
        '\t\t\t60 ; Retry\n'
        '\t\t\t360000 ; Expire\n'
        '\t\t\t10 ); Negative TTL\n'
        '\t\tNS\tns.prolo.\n'
        '\n'
        '; Auto-generated zone\n'
    )

    zone = ZONE_HEADER % { 'serial': serial }
    zone += '\n'.join('\t'.join(record) for record in records)
    zone += '\n'

    with open(path, 'w') as fp:
        fp.write(zone)


def build_alien_revdns_zone():
    """Build the reverse DNS zone for the alien IP range.

    It is fully static and could in theory be only built once, but meh.
    """
    records = [
        (str(i), 'IN', 'PTR', 'unknown-%d.alien.prolo.' % i)
        for i in range(1, 254)
    ]
    records.append(('254', 'IN', 'PTR', 'gw.alien.prolo.'))
    build_zone('250.168.192.in-addr.arpa', records)


def build_machines_revdns_zone(machines, mtype, ip):
    machines = [m for m in machines if m['mtype'] == mtype]
    if mtype == 'user':  # hack: orga machines are like user machines
        machines.extend(m for m in machines if m['mtype'] == 'orga')

    records = [
        (m['ip'].split('.')[-1], 'IN', 'PTR', '%s.prolo.' % m['hostname'])
        for m in machines
    ]
    build_zone(ip + '.in-addr.arpa', records)


def build_alien_prolo_zone():
    """Alien machines just need to be able to access netboot.
    """

    build_zone('prolo_alien', [('netboot', 'IN', 'A', '192.168.250.254'),
                               ('ns', 'IN', 'A', '192.168.250.254')])


def build_normal_prolo_zone(machines):
    records = []
    for m in machines:
        names = [m['hostname']] + [s.strip() for s in m['aliases'].split(',')]
        for n in names:
            records.append((n, 'IN', 'A', m['ip']))
    build_zone('prolo_normal', records)


def reload_zones():
    os.system('rndc reload')


def update_dns_config(machines_map, metadata):
    machines = machines_map.values()

    logging.warning("MDB update received, generating zones")
    build_alien_revdns_zone()
    build_machines_revdns_zone(machines, 'user', '0.168.192')
    build_machines_revdns_zone(machines, 'service', '1.168.192')
    build_machines_revdns_zone(machines, 'cluster', '2.168.192')
    build_alien_prolo_zone()
    build_normal_prolo_zone(machines)

    logging.warning("Reloading zones")
    reload_zones()

if __name__ == '__main__':
    prologin.log.setup_logging('mdbdns')
    prologin.mdbsync.connect().poll_updates(update_dns_config)
