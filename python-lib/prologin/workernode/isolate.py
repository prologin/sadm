# This file is part of Prologin-SADM.
#
# Copyright (c) 2015 Antoine Pietri <antoine.pietri@prologin.org>
# Copyright (c) 2015 Association Prologin <info@prologin.org>
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
import itertools

from . import tools

MAX_BOX_ID = 100

class Isolator:
    def __init__(self):
        self.last_box_id = 0

    @asyncio.coroutine
    def communicate(self, cmdline, time_limit=None, mem_limit=None,
                    allowed_dirs=None, processes=1, **kwargs):
        if allowed_dirs is None:
            allowed_dirs = []
        self.last_box_id = (self.last_box_id + 1) % MAX_BOX_ID
        box_id = self.last_box_id

        isolate_base = ['isolate', '--box-id', str(box_id), '--cg']
        isolate_init = isolate_base + ['--init']
        isolate_cleanup = isolate_base + ['--cleanup']

        isolate_run = isolate_base
        isolate_run += list(itertools.chain(*[('-d', d) for d in allowed_dirs]))
        if mem_limit is not None:
            isolate_run += ['--mem', str(mem_limit)]
        if time_limit is not None:
            isolate_run += ['--wall-time', str(time_limit)]
        isolate_run += [
            '--full-env',
            '--processes={}'.format(str(processes)),
            '--run', '--'
        ]
        isolate_run += cmdline

        yield from tools.communicate(isolate_init)
        exitcode, stdout = yield from tools.communicate(isolate_run, **kwargs)
        yield from tools.communicate(isolate_cleanup)
        return exitcode, stdout


isolator = Isolator()

@tools.add_coro_timeout
@asyncio.coroutine
def communicate(*args, **kwargs):
    return (yield from isolator.communicate(*args, **kwargs))
