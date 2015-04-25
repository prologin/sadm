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

import json
import prologin.mdb.receivers  # To connect our receivers

from django.http import HttpResponse, HttpResponseForbidden
from django.http import HttpResponseBadRequest, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
from prologin.mdb.models import Machine, VolatileSetting


@csrf_exempt
def query(request):
    args = request.REQUEST
    machines = Machine.objects.filter(**args)  # TODO(delroth): secure?
    machines = [m.to_dict() for m in machines]
    return HttpResponse(json.dumps(machines), content_type='application/json')


@csrf_exempt
def register(request):
    try:
        key = VolatileSetting.objects.get(key='allow_self_registration')
        authorized = key.value_bool
    except VolatileSetting.DoesNotExist:
        authorized = False

    if not authorized:
        return HttpResponseForbidden('self registration is disabled',
                                     content_type='text/plain')

    for field in ('hostname', 'mac', 'rfs', 'hfs', 'room', 'mtype'):
        if field not in request.REQUEST:
            return HttpResponseBadRequest('missing field %r' % field,
                                          content_type='text/plain')

    machine = Machine()
    machine.hostname = request.REQUEST['hostname']
    machine.mac = request.REQUEST['mac']
    machine.rfs = int(request.REQUEST['rfs'])
    machine.hfs = int(request.REQUEST['hfs'])
    machine.room = request.REQUEST['room']
    machine.mtype = request.REQUEST['mtype']
    try:
        machine.allocate_ip()
    except Exception:
        return HttpResponseServerError('unable to allocate an IP address',
                                       content_type='text/plain')

    try:
        machine.save()
    except Exception:
        return HttpResponseServerError('unable to register, duplicate name?',
                                       content_type='text/plain')

    return HttpResponse(machine.ip, content_type='text/plain')
