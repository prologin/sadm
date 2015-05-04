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


from prometheus_client import start_http_server, Summary, Gauge

hfs_migrate_remote_user = Summary(
    'hfs_migrate_remote_user_summary',
    'Summary of migrated (received) hfs',
    labelnames=('user', 'hfs'))

hfs_migrate_user = Summary(
    'hfs_migrate_user_summary',
    'Summary of migrated (sent) hfs',
    labelnames=('user', 'hfs'))

hfs_get_hfs = Summary(
    'hfs_get_hfs_summary',
    'Summary of hfs starts',
    labelnames=('user', 'user_type', 'hfs'))

hfs_new_user = Summary(
    'hfs_new_user',
    'Summary new nbd creations',
    labelnames=('user', 'user_type'))

hfs_running_nbd = Gauge(
    'hfs_running_nbd_gauge',
    'Number of nbd served by this hfs server')

def monitoring_start(addr):
    start_http_server(9030, addr)
