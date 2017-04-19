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
import subprocess


def add_coro_timeout(coro):
    async def coro_(*args, coro_timeout=None, **kwargs):
        return (await asyncio.wait_for(coro(*args, **kwargs),
                                       timeout=coro_timeout))
    return coro_


async def communicate_process(proc, *, data=None, max_len=None,
                              truncate_message=''):
    # Send stdin
    if data:
        proc.stdin.write(data.encode())
        await proc.stdin.drain()
        proc.stdin.close()

    # Receive stdout
    stdout = bytearray()
    while True:
        to_read = 4096
        if max_len is not None:
            to_read = min(to_read, max_len - len(stdout))
            if not to_read:
                break
        chunk = await proc.stdout.read(to_read)
        if not chunk:
            break
        stdout.extend(chunk)

    if not to_read:
        stdout += truncate_message.encode()

    exitcode = await proc.wait()
    return (exitcode, stdout)


async def create_process(cmdline, *, data=None, **kwargs):
    return (await asyncio.create_subprocess_exec(*cmdline,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, **kwargs))


@add_coro_timeout
async def communicate(cmdline, *, data=None, max_len=None,
                      truncate_message='', **kwargs):
    proc = await create_process(cmdline, **kwargs)
    return (await communicate_process(proc, data=data, max_len=max_len,
            truncate_message=''))
