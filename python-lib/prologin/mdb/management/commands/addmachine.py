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

import time

from django.core.management.base import BaseCommand, CommandError
from prologin.mdb.models import Machine
from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--hostname', help='Machine name'),
        make_option('--aliases', help='DNS aliases (comma separated)'),
        make_option('--ip', help='Machine IP address'),
        make_option('--mac', help='Machine MAC address'),
        make_option('--rfs', help='RFS used by the machine'),
        make_option('--hfs', help='HFS used by the machine'),
        make_option('--mtype',
                    help='Machine type (user/orga/cluster/service)'),
        make_option('--room',
                    help='Machine location (pasteur/alt/cluster/other)'),
    )

    def get_opt(self, options, name):
        if options.get(name, None) is None:
            raise CommandError('please specify --%s' % name)
        return options[name]

    def handle(self, *args, **options):
        m = Machine()
        for attr in ('hostname', 'aliases', 'ip', 'mac', 'rfs', 'hfs',
                     'mtype', 'room'):
            setattr(m, attr, self.get_opt(options, attr))
        m.save()

        # Sleep to let time for the sync message
        time.sleep(1)
