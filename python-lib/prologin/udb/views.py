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
import prologin.config
import prologin.timeauth
import prologin.udb.receivers  # To connect our receivers

from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from prologin.udb.models import User

CFG = prologin.config.load('udb-client-auth')

@csrf_exempt
def query(request):
    args = dict(request.REQUEST)

    # If a HMAC is provided, check for authentication. If checking fails,
    # return a HTTP 403 error.
    hmac = args.pop('hmac', None)
    auth_required = hmac is not None
    if auth_required:
        shared_secret = CFG['shared_secret'].encode('utf-8')
        if not prologin.timeauth.check_token(hmac, shared_secret):
            return HttpResponseForbidden(
                'hmac is invalid',
                content_type='text/plain'
            )

    users = User.objects.filter(**args)  # TODO(delroth): secure?
    users = [m.to_dict() for m in users]

    # Only authenticated clients shall read passwords.
    if not auth_required:
        for u in users:
            del u['password']

    return HttpResponse(json.dumps(users), content_type='application/json')
