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

import abc
import os
import os.path
import time

from base64 import b64encode
from pathlib import Path


def get_champion_path(config, user, cid):
    return Path(
        config['contest']['directory'],
        config['contest']['game'],
        'champions',
        user,
        str(cid),
    )


def get_match_path(config, match_id):
    match_id_high = "{:03}".format(match_id // 1000)
    match_id_low = "{:03}".format(match_id % 1000)
    return Path(
        config['contest']['directory'],
        config['contest']['game'],
        'matches',
        match_id_high,
        match_id_low,
    )


class Task(abc.ABC):
    def __init__(self, timeout=None):
        self.start_time = None
        self.timeout = timeout
        self.executions = 0
        self.error = None

    @property
    @abc.abstractmethod
    def slots_taken(self):
        raise NotImplementedError

    async def execute(self):
        self.start_time = time.monotonic()
        self.executions += 1
        self.error = None

    @abc.abstractmethod
    async def redispatch(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def fail(self):
        raise NotImplementedError

    def has_timeout(self):
        return (
            self.timeout is not None
            and self.start_time is not None
            and time.monotonic() > self.start_time + self.timeout
        )

    def has_error(self):
        return self.error is not None


class CompilationTask(Task):
    def __init__(self, config, db, user, champ_id):
        super().__init__(timeout=config["worker"]["compilation_timeout_secs"])
        self.db = db
        self.user = user
        self.champ_id = champ_id
        self.champ_path = get_champion_path(config, user, champ_id)

    @property
    def slots_taken(self):
        return 1

    async def execute(self, master, worker):
        await super().execute()

        ctgz = b64encode(
            (self.champ_path / 'champion.tgz').read_bytes()
        ).decode()

        await self.db.execute(
            "set_champion_status",
            {"champion_status": "pending", "champion_id": self.champ_id},
        )

        await worker.rpc.compile_champion(self.user, self.champ_id, ctgz)

    async def redispatch(self):
        await self.db.execute(
            "set_champion_status",
            {"champion_status": "new", "champion_id": self.champ_id},
        )

    async def fail(self):
        await self.db.execute(
            "set_champion_status",
            {"champion_status": "failed", "champion_id": self.champ_id},
        )

    def __repr__(self):
        return f"<Compilation: id={self.champ_id}, user={self.user}>"


class MatchTask(Task):
    def __init__(self, config, db, mid, players, map_contents):
        super().__init__(timeout=config["worker"]["match_timeout_secs"])
        self.db = db
        self.mid = mid
        self.map_contents = map_contents
        self.players = {}
        self.match_path = get_match_path(config, self.mid)

        for (cid, mpid, user) in players:
            ctgz = b64encode(
                (
                    get_champion_path(config, user, cid)
                    / 'champion-compiled.tgz'
                ).read_bytes()
            ).decode()
            self.players[mpid] = (cid, ctgz)

    def __repr__(self):
        return f"<Match: id={self.mid}>"

    @property
    def slots_taken(self):
        return 5

    async def execute(self, master, worker):
        await super().execute()

        try:
            os.makedirs(self.match_path)
        except OSError:
            pass

        try:
            await worker.rpc.run_match(
                self.mid, self.players, self.map_contents
            )
        except Exception as e:
            self.error = f'Could not dispatch match: {e}'
            return

        # Set the match as pending *after* the RPC call has succeeded.
        await self.db.execute(
            "set_match_status",
            {"match_status": "pending", "match_id": self.mid},
        )

    async def redispatch(self):
        print(f"Redispatching {self}")
        await self.db.execute(
            "set_match_status", {"match_status": "new", "match_id": self.mid}
        )

    async def fail(self):
        await self.db.execute(
            "set_match_status",
            {"match_status": "failed", "match_id": self.mid},
        )
