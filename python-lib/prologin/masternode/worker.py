# -*- encoding: utf-8 -*-
# This file is part of Prologin-SADM.
#
# Copyright (c) 2013 Antoine Pietri <antoine.pietri@prologin.org>
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
import prologin.rpc.client
import time

from . import task

class Worker(object):
    def __init__(self, hostname, port, slots, max_slots, config):
        self.hostname = hostname
        self.port = port
        self.slots = slots
        self.max_slots = max_slots
        self.tasks = []
        self.keep_alive()
        self.config = config
        self.rpc = prologin.rpc.client.Client("http://{}:{}/".format(
            self.hostname, self.port),
            secret=self.config['master']['shared_secret'].encode('utf-8'),
            async=True)

    @property
    def usage(self):
        return 1.0 - (float(self.slots) / self.max_slots)

    @asyncio.coroutine
    def accessible(self):
        try:
            return (yield from self.rpc.accessible())
        except:
            return False

    def update(self, slots, max_slots):
        self.slots = slots
        self.max_slots = max_slots
        self.keep_alive()

    def keep_alive(self):
        self.last_heartbeat = time.time()

    def is_alive(self, timeout):
        return (time.time() - self.last_heartbeat) < timeout

    def can_add_task(self, task):
        return self.slots >= task.slots_taken

    def add_task(self, master, task):
        self.slots -= task.slots_taken
        self.tasks.append(task)
        asyncio.Task(task.execute(master, self))

    def remove_compilation_task(self, champ_id):
        new = []
        for t in self.tasks:
            if isinstance(t, task.CompilationTask):
                if t.champ_id == champ_id:
                    continue
            new.append(t)
        self.tasks = new

    def remove_match_task(self, mid):
        new = []
        for t in self.tasks:
            if isinstance(t, task.MatchTask):
                if t.mid == mid:
                    continue
            new.append(t)
        self.tasks = new

    def remove_player_task(self, mpid):
        new = []
        for t in self.tasks:
            if isinstance(t, task.PlayerTask):
                if t.mpid == mpid:
                    continue
            new.append(t)
        self.tasks = new

    def __repr__(self):
        return '<Worker: {}:{}>'.format(self.hostname, self.port)
