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


from prometheus_client import Gauge
from .models import Champion, Match

concours_champion_status_count = Gauge(
    'concours_champion_status_count',
    'Count of champion by status',
    labelnames=('status',))
for status in ('new', 'pending', 'ready', 'error'):
    labels = {'status': status}
    concours_champion_status_count.labels(labels).set_function(
        lambda status=status: len(Champion.objects.filter(status=status)))

concours_match_status_count = Gauge(
    'concours_match_status_count',
    'Count of matches in by status',
    labelnames=('status',))
for status in ('creating', 'new', 'pending', 'done'):
    labels = {'status': status}
    concours_match_status_count.labels(labels).set_function(
        lambda status=status: len(Match.objects.filter(status=status)))
