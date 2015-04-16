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

from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render_to_response
from prologin.homepage.models import Link
import datetime


def home(request):
    links = Link.objects.filter(Q(contest_only=False)
                                | Q(contest_only=settings.CONTEST_MODE))
    links = links.order_by('display_order', 'name')
    target_date = timezone.make_aware(datetime.datetime.strptime(
        settings.COUNTDOWN_TO, "%Y-%m-%d %H:%M:%S"))
    target_date = target_date.isoformat()
    return render_to_response('home.html', {'links': links,
                                            'target_date': target_date})
