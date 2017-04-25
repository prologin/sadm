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

import prologin.rpc.server
import prologin.mdb.receivers  # To connect our receivers
from prologin.mdb.models import Machine, Switch, VolatileSetting
from prologin.utils.django import check_filter_fields


class MDBServer(prologin.rpc.server.BaseRPCApp):
    @prologin.rpc.remote_method(auth_required=False)
    async def query(self, **kwargs):
        """Query the MDB using the Django query syntax. The possible fields
        are:
          hostname: the machine name and any of its aliases
          ip: the machine IP address
          aliases: the machine aliases
          mac: the machine MAC address
          rfs: nearest root file server
          hfs: nearest home file server
          mtype: machine type, either user/orga/cluster/service
          room: physical room location, either pasteur/alt/cluster/other
        """
        fields = {'hostname', 'ip', 'aliases', 'mac', 'rfs', 'hfs', 'mtype',
                  'room'}
        check_filter_fields(fields, kwargs)

        machines = Machine.objects.filter(**kwargs)
        machines = [m.to_dict() for m in machines]
        return machines

    @prologin.rpc.remote_method(auth_required=False)
    async def switches(self, **kwargs):
        """Query the MDB for switches using the Django query syntax. The
        possible fields are:

          name: the name of the switch
          chassis: the chassis ID
          rfs: associated root file server
          hfs: associated home file server
          room: physical room location, either pasteur/alt/cluster/other
        """
        fields = {'name', 'chassis', 'rfs', 'hfs', 'room'}
        check_filter_fields(fields, kwargs)
        switches = Switch.objects.filter(**kwargs)
        switches = [s.to_dict() for s in switches]
        return switches

    @prologin.rpc.remote_method(auth_required=False)
    async def register(self, hostname, mac, rfs, hfs, room, mtype):
        try:
            key = VolatileSetting.objects.get(key='allow_self_registration')
            authorized = key.value_bool
        except VolatileSetting.DoesNotExist:
            authorized = False

        if not authorized:
            raise RuntimeError('self registration is disabled')

        machine = Machine()
        machine.hostname = hostname
        machine.mac = mac
        machine.rfs = rfs
        machine.hfs = hfs
        machine.room = room
        machine.mtype = mtype
        try:
            machine.allocate_ip()
        except Exception:
            raise RuntimeError('unable to allocate an IP address')

        try:
            machine.save()
        except Exception:
            raise RuntimeError('unable to register, duplicate name?')

        return machine.ip
