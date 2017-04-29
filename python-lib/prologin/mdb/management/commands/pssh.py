# -*- encoding: utf-8 -*-
# Copyright (c) 2014 Rémi Audebert <halfr@prologin.org>
# Copyright (c) 2014 Association Prologin <info@prologin.org>
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

import subprocess
import time

from django.core.management.base import BaseCommand
from prologin.mdb.models import Machine


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('command', nargs='+', help='Command to run')

        parser.add_argument('--hostname', help='Machine name')
        parser.add_argument('--ip', help='Machine IP address')
        parser.add_argument('--mac', help='Machine MAC address')
        parser.add_argument('--rfs', help='RFS used by the machines')
        parser.add_argument('--hfs', help='HFS used by the machines')
        parser.add_argument('--user', help='SSH as this user (default: root)')
        parser.add_argument('--mtype',
                        help='Machines type (user/orga/cluster/service)')
        parser.add_argument('--room',
                        help='Machines location (pasteur/alt/cluster/other')

    def handle(self, *args, **options):
        user = options['user'] or 'root'
        kwargs = {}
        for attr in ('hostname', 'ip', 'mac', 'rfs', 'hfs', 'mtype', 'room'):
            if options.get(attr, None) is not None:
                kwargs[attr+'__iregex'] = options[attr]
        machines = Machine.objects.filter(**kwargs)

        print("Warning: running command on %s in 3sec..." % machines)
        time.sleep(3)

        ips = ' '.join([machine.ip for machine in machines])
        command = ' '.join(options['command'])
        p = subprocess.Popen('pssh -l %s -H "%s" %s' % (user, ips, command),
                             shell=True)
        p.wait()
