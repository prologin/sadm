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

from prometheus_client import start_http_server, Summary, Gauge

workernode_compile_champion_summary = Summary(
    'workernode_compile_champion_summary',
    'Summary of compile champion task')

workernode_run_server_summary = Summary(
    'workernode_run_server_count',
    'Summary of server task')

workernode_run_client_summary = Summary(
    'workernode_run_client_count',
    'Summary of client task')

workernode_slots = Gauge(
    'workernode_slots',
    'Number of available slots')


def monitoring_start():
    start_http_server(9020)
