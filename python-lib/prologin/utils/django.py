# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Antoine Pietri <antoine.pietri@prologin.org>
# Copyright (c) 2016 Association Prologin <info@prologin.org>
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

def get_request_args(request):
    '''Returns a dict containing the arguments of a request from GET/POST.'''
    return {k: v[0] for k, v in {**request.POST, **request.GET}.items() if v}

def check_filter_fields(fields, kwargs):
    for q in kwargs:
        base = q.split('_')[0]
        if base not in fields:
            raise ValueError('%r is not a valid query argument' % q)
