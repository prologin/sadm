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
import os
import os.path

from base64 import b64decode, b64encode


def champion_path(config, user, cid):
    return os.path.join(config['contest']['directory'],
            config['contest']['game'], 'champions', user, str(cid),
            'champion.tgz')

def champion_compiled_path(config, user, cid):
    return os.path.join(config['contest']['directory'],
            config['contest']['game'], 'champions', user, str(cid),
            'champion-compiled.tgz')


def clog_path(config, user, cid):
    return os.path.join(config['contest']['directory'],
            config['contest']['game'], 'champions', user, str(cid),
            'compilation.log')


def match_path(config, match_id):
    match_id_high = "{:03}".format(match_id // 1000)
    match_id_low = "{:03}".format(match_id % 1000)
    return os.path.join(config['contest']['directory'],
            config['contest']['game'], 'matches', match_id_high, match_id_low)


class CompilationTask:
    def __init__(self, config, user, champ_id):
        self.config = config
        self.user = user
        self.champ_id = champ_id
        self.champ_path = champion_path(config, user, champ_id)

    @property
    def slots_taken(self):
        return 1

    @asyncio.coroutine
    def execute(self, master, worker):
        ctgz = ''
        with open(self.champ_path, 'rb') as f:
            ctgz = b64encode(f.read()).decode()
        yield from worker.rpc.compile_champion(self.user,
                self.champ_id, ctgz)

    def __repr__(self):
        return "<Compilation: {}>".format(self.champ_id)


class PlayerTask:
    def __init__(self, config, match_id, pl_id, ip, req_port, sub_port, user,
            cid, opts, file_opts):
        self.match_id = match_id
        self.hostname = ip
        self.req_port = req_port
        self.sub_port = sub_port
        self.mpid = pl_id
        self.opts = opts
        self.file_opts = file_opts
        self.champ_path = champion_compiled_path(config, user, cid)
        self.cid = cid

    @property
    def slots_taken(self):
        return 2 # It's usually fairly intensive, take 2 slots

    @asyncio.coroutine
    def execute(self, master, worker):
        ctgz = ''
        with open(self.champ_path, 'rb') as f:
            ctgz = b64encode(f.read()).decode()
        yield from worker.rpc.run_client(self.match_id, self.mpid,
                self.hostname, self.req_port, self.sub_port, self.cid, ctgz,
                self.opts, self.file_opts)


class MatchTask:
    def __init__(self, config, mid, players, opts, file_opts):
        self.config = config
        self.mid = mid
        self.players = players
        self.opts = opts
        self.file_opts = file_opts
        self.player_tasks = set()

    @property
    def slots_taken(self):
        return 1 # Only the server is launched by this task

    @asyncio.coroutine
    def execute(self, master, worker):
        try:
            os.makedirs(match_path(self.config, self.mid))
        except OSError:
            pass

        master.matches[self.mid] = self
        req_port, sub_port = yield from worker.rpc.get_ports(2)

        yield from worker.rpc.run_server(req_port, sub_port, self.mid,
                len(self.players), self.opts, self.file_opts)
        for (cid, mpid, user) in self.players:
            # on error, prevent launching several times the players
            if mpid in self.player_tasks:
                continue
            self.player_tasks.add(mpid)

            t = PlayerTask(self.config, self.mid, mpid, worker.hostname,
                    req_port, sub_port, user, cid, self.opts, self.file_opts)
            master.worker_tasks.append(t)
        master.to_dispatch.set()
        del master.matches[self.mid]
