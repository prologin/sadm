# -*- encoding: utf-8 -*-
# This file is part of Prologin-SADM.
#
# Copyright (c) 2014-2015 Antoine Pietri <antoine.pietri@prologin.org>
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
import time

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


class Task:
    def __init__(self, timeout=None):
        self.start_time = None
        self.timeout = timeout
        self.executions = 0

    def execute(self):
        self.start_time = time.time()
        self.executions += 1

    def has_timeout(self):
        return (self.timeout is not None and
                self.start_time is not None and
                time.time() > self.start_time + self.timeout)


class CompilationTask(Task):
    def __init__(self, config, user, champ_id):
        super().__init__(timeout=config['worker']['compilation_timeout_secs'])
        self.user = user
        self.champ_id = champ_id
        self.champ_path = champion_path(config, user, champ_id)

    @property
    def slots_taken(self):
        return 1

    @asyncio.coroutine
    def execute(self, master, worker):
        super().execute()
        ctgz = ''
        with open(self.champ_path, 'rb') as f:
            ctgz = b64encode(f.read()).decode()
        yield from worker.rpc.compile_champion(self.user,
                self.champ_id, ctgz)

    def __repr__(self):
        return "<Compilation: {}>".format(self.champ_id)


class MatchTask(Task):
    def __init__(self, config, mid, players, opts, file_opts):
        super().__init__(timeout=config['worker']['match_timeout_secs'])
        self.mid = mid
        self.opts = opts
        self.file_opts = file_opts
        self.players = {}
        self.match_path = match_path(config, self.mid)

        for (cid, mpid, user) in players:
            cpath = champion_compiled_path(config, user, cid)
            ctgz = ''
            with open(cpath, 'rb') as f:
                ctgz = b64encode(f.read()).decode()
            self.players[mpid] = (cid, ctgz)

    @property
    def slots_taken(self):
        return 5

    @asyncio.coroutine
    def execute(self, master, worker):
        super().execute()
        try:
            os.makedirs(self.match_path)
        except OSError:
            pass

        yield from worker.rpc.run_match(self.mid, self.players, self.opts,
                                        self.file_opts)
