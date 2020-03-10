# Copyright (c) 2015 Rémi Audebert <remi.audebert@prologin.org>
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

"""Ansible dynmaic inventory from the machine database (mdb).

References:

    - http://docs.ansible.com/intro_dynamic_inventory.html
    - http://docs.ansible.com/developing_inventory.html
"""

import json

from django.core.management.base import BaseCommand

from prologin.mdb.models import Machine


class Command(BaseCommand):
    help = 'Ansible dynamic inventory from mdb'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list', action='store_true', help='display list of hosts'
        )

    def handle(self, *args, **kwargs):
        ret = {
            k: {
                'hosts': [],
                'vars': {
                    'ansible_python_interpreter': 'python2',
                    'remote_tmp': '/tmp/.ansible/tmp',
                },
            }
            for k in ('orga', 'user', 'service')
        }
        # If this field is not present in the --list output ansible will iterate
        # very slowly over all the hosts and call this script to get their
        # hostvars. See https://github.com/ansible/ansible/issues/9291
        ret['_meta'] = {'hostvars': {}}

        machines = Machine.objects.all()
        for machine in machines:
            ret[machine.mtype]['hosts'].append(machine.hostname)

        ret_json = json.dumps(ret)
        print(ret_json)
