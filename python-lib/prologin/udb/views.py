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
import prologin.udb.receivers  # To connect our receivers
from prologin.udb.models import User
from prologin.utils.django import check_filter_fields


class UDBServer(prologin.rpc.server.BaseRPCApp):
    def __init__(self, secret, **kwargs):
        super().__init__(secret=secret, **kwargs)

    def get_users(self, **kwargs):
        fields = {'login', 'uid', 'group', 'shell', 'ssh_key', 'id'}
        check_filter_fields(fields, kwargs)
        users = User.objects.filter(**kwargs)
        users = [m.to_dict() for m in users]
        return users

    @prologin.rpc.remote_method(auth_required=False)
    async def query(self, **kwargs):
        users = self.get_users(**kwargs)
        for u in users:
            del u['password']
        return users

    @prologin.rpc.remote_method
    async def query_private(self, **kwargs):
        return self.get_users(**kwargs)
