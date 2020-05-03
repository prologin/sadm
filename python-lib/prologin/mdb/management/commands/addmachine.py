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

import time

from django.core.management.base import BaseCommand, CommandError
from prologin.mdb.models import Machine


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--hostname', help='machine_name')
        parser.add_argument('--aliases', help='DNS aliases (comma separated)')
        parser.add_argument('--ip', help='Machine IP address')
        parser.add_argument('--mac', help='Machine MAC address')
        parser.add_argument('--rfs', help='RFS used by the machine')
        parser.add_argument('--hfs', help='HFS used by the machine')
        parser.add_argument(
            '--mtype', help='Machine type (user/orga/cluster/service)'
        )
        parser.add_argument(
            '--room', help='Machine location (pasteur/alt/cluster/other)'
        )

        parser.add_argument(
            '--update',
            action='store_true',
            help='If specified, also update already existing machines.',
        )

    def get_opt(self, options, name):
        if name not in options:
            raise CommandError('please specify --%s' % name)
        return options[name]

    def handle(self, *args, **options):
        m = Machine()
        updating = False
        if options['update']:
            try:
                m = Machine.objects.get(hostname=options['hostname'])
                updating = True
            except Machine.DoesNotExist:
                pass

        update_fields = ('aliases', 'rfs', 'hfs', 'mtype', 'room')
        create_fields = update_fields + ('hostname', 'mac')

        if updating:
            for attr in update_fields:
                if options.get(attr):
                    setattr(m, attr, options[attr])
        else:
            for attr in create_fields:
                setattr(m, attr, self.get_opt(options, attr))

            if not options.get('ip'):
                m.allocate_ip()
            else:
                m.ip = options['ip']

        m.full_clean()
        m.save()

        # Sleep to let time for the sync message
        time.sleep(1)
