# -*- encoding: utf-8 -*-
# This file is part of Prologin-SADM.
#
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

from functools import wraps

from prometheus_client import start_http_server, Summary


rpc_call_in = Summary(
        'rpc_call_in',
        'Summary of the rpc calls received',
        ['method'])

def _observe_rpc_call_in(f):
    @wraps(f)
    def _wrapper(self, method_name):
        with rpc_call_in.labels({'method': method_name}).time():
            return f(self, method_name)

    return _wrapper


rpc_call_out = Summary(
        'rpc_call_out',
        'Summary of the rpc calls sent')

# Monitoring is started by the application using the rpc library
