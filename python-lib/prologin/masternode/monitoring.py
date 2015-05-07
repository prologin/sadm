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


from prometheus_client import start_http_server, Summary, Gauge, Counter

masternode_workers = Gauge(
    'masternode_workers',
    'Number of available workers')

masternode_tasks = Gauge(
    'masternode_tasks',
    'Number of masternode tasks')

masternode_task_redispatch = Counter(
    'masternode_task_redispatch',
    'Number of redispatched tasks')

masternode_request_compilation_task = Counter(
    'masternode_request_compilation_task',
    'Number of compilation requests')

masternode_match_done_file = Summary(
    'masternode_match_done_file',
    'Summary of match done files write')

masternode_client_done_file = Summary(
    'masternode_client_done_file',
    'Summary of client done file write')

masternode_match_done_db = Summary(
    'masternode_match_done_db',
    'Summary of match done database access')

masternode_worker_timeout = Gauge(
    'masternode_worker_timeout',
    'Number of workers timeout')

def monitoring_start():
    start_http_server(9021)
