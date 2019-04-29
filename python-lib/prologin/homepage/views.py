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
from django.views.generic.list import ListView
import datetime

from prologin.homepage import models


class HomeView(ListView):
    template_name = 'home.html'
    context_object_name = 'links'
    queryset = (models.Link.objects.filter(
        Q(contest_only=False)
        | Q(contest_only=settings.CONTEST_MODE)).order_by(
            'display_order', 'name'))

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        dt = datetime.datetime.strptime(settings.COUNTDOWN_TO,
                                        "%Y-%m-%d %H:%M:%S")
        context['target_date'] = timezone.make_aware(dt).isoformat()
        return context
