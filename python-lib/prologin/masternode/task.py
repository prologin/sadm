# -*- encoding: utf-8 -*-
# This file is part of Prologin-SADM.
#
# Copyright (c) 2014 Antoine Pietri <antoine.pietri@prologin.org>
# Copyright (c) 2011 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2011 Association Prologin <info@prologin.org>
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

import asyncio


class CompilationTask:
    def __init__(self, champ_id, champ_tgz):
        self.champ_tgz = champ_tgz
        self.champ_id = champ_id

    @property
    def slots_taken(self):
        return 1

    @asyncio.coroutine
    def execute(self, master, worker):
        yield from worker.rpc.compile_champion(self.champ_id, self.champ_tgz)

    def __repr__(self):
        return "<Compilation: {}>".format(self.champ_id)


class PlayerTask:
    def __init__(self, match_id, pl_id, ip, req_port, sub_port, ctgz, opts):
        self.match_id = match_id
        self.hostname = ip
        self.req_port = req_port
        self.sub_port = sub_port
        self.ctgz = ctgz
        self.pl_id = pl_id
        self.opts = opts

    @property
    def slots_taken(self):
        return 2 # It's usually fairly intensive, take 2 slots

    @asyncio.coroutine
    def execute(self, master, worker):
        yield from worker.rpc.run_client(self.match_id, self.pl_id,
            self.hostname, self.req_port, self.sub_port, self.ctgz, self.opts)


class MatchTask:
    def __init__(self, config, mid, players, opts):
        self.config = config
        self.contest = config['master']['contest']
        self.mid = mid
        self.players = players
        self.opts = opts
        self.player_tasks = set()

    @property
    def slots_taken(self):
        return 1 # Only the server is launched by this task

    @asyncio.coroutine
    def execute(self, master, worker):
        master.matches[self.mid] = self
        req_port = yield from worker.rpc.available_port()
        sub_port = yield from worker.rpc.available_port()

        yield from worker.rpc.run_server(req_port, sub_port, self.mid,
                self.opts)
        for (cid, mpid, user) in self.players:
            # on error, prevent launching several times the players
            if mpid in self.player_tasks:
                continue
            self.player_tasks.add(mpid)

            t = PlayerTask(self.config, self.mid, worker.hostname, req_port,
                sub_port, cid, mpid, user, self.opts)
            master.worker_tasks.append(t)
        master.to_dispatch.set()
        del master.matches[self.mid]
