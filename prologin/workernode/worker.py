# This file is part of Prologin-SADM.
#
# Copyright (c) 2013-2020 Antoine Pietri <antoine.pietri@prologin.org>
# Copyright (c) 2011 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2011-2014 Association Prologin <info@prologin.org>
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
import functools
import logging
import logging.handlers
import prologin.rpc.client
import prologin.rpc.server
import socket
import time

from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
)

from . import operations

from .monitoring import (
    workernode_slots,
    workernode_compile_champion_summary,
    workernode_run_match_summary,
)


def async_work(func=None, slots=0):
    if func is None:
        return functools.partial(async_work, slots=slots)

    @functools.wraps(func)
    async def mktask(self, *args, **kwargs):
        async def wrapper(self, *wargs, **wkwargs):
            if self.slots < slots:
                logging.warning('not enough slots to start the required job')
                return
            logging.debug('starting a job for %s slots', slots)
            self.slots -= slots
            workernode_slots.set(self.slots)
            await self.update_master()
            try:
                await func(self, *wargs, **wkwargs)
            finally:
                self.slots += slots
                workernode_slots.set(self.slots)
                await self.update_master()

        asyncio.Task(wrapper(self, *args, **kwargs), loop=self.loop)
        return slots

    return mktask


class WorkerNode(prologin.rpc.server.BaseRPCApp):
    def __init__(self, *args, config=None, **kwargs):
        secret = config['master']['shared_secret'].encode()
        super().__init__(*args, secret=secret, **kwargs)
        self.config = config
        self.interval = config['master']['heartbeat_secs']
        self.hostname = socket.gethostname()
        self.port = config['worker']['port']
        self.slots = self.max_slots = config['worker']['available_slots']
        self.matches = {}
        self.loop = asyncio.get_event_loop()
        self.master = self.get_master()

    def run(self):
        logging.info('worker listening on %s', self.config['worker']['port'])
        asyncio.Task(self.send_heartbeat())
        super().run(port=self.config['worker']['port'])

    def stop(self):
        self.loop.stop()

    def get_worker_infos(self):
        return (self.hostname, self.port, self.slots, self.max_slots)

    def get_master(self):
        config = self.config
        host, port = (config['master']['host'], config['master']['port'])
        url = "http://{}:{}/".format(host, port)
        return prologin.rpc.client.Client(
            url, secret=config['master']['shared_secret'].encode('utf-8')
        )

    async def update_master(self):
        try:
            await self.master.update_worker(self.get_worker_infos())
        except socket.error:
            logging.warning('master down, cannot update it')

    async def send_heartbeat(self):
        logging.debug(
            'sending heartbeat to the server, %s/%s slots',
            self.slots,
            self.max_slots,
        )
        first_heartbeat = True
        while True:
            try:
                await self.master.heartbeat(
                    self.get_worker_infos(), first_heartbeat
                )
                first_heartbeat = False
            except socket.error:
                logging.warning(
                    'master down, retrying heartbeat in %ss', self.interval
                )

            await asyncio.sleep(self.interval)

    @prologin.rpc.remote_method
    async def reachable(self):
        return True

    @prologin.rpc.remote_method
    @async_work(slots=1)
    async def compile_champion(self, user, cid, ctgz):
        logging.info('compilation %s: starting', cid)
        compile_champion_start = time.monotonic()
        result = await operations.compile_champion(self.config, ctgz)
        workernode_compile_champion_summary.observe(
            max(time.monotonic() - compile_champion_start, 0)
        )
        logging.info('compilation %s: done', cid)

        @retry(
            reraise=True,
            stop=stop_after_attempt(15),
            wait=wait_fixed(10),
            retry=retry_if_exception_type(socket.error),
        )
        async def send_master_result():
            await self.master.compilation_done(
                self.get_worker_infos(),
                user,
                cid,
                result,
            )

        try:
            await send_master_result()
        except socket.error:
            logging.warning('master down, cannot send compiled %s', cid)
        else:
            logging.info('compilation %s: sent to masternode', cid)

    @prologin.rpc.remote_method
    @async_work(slots=5)
    async def run_match(self, match_id, players, map_contents=None):
        logging.info('match %s: started', match_id)
        run_match_start = time.monotonic()
        result = await operations.spawn_match(
            self.config, players, map_contents
        )
        workernode_run_match_summary.observe(
            max(time.monotonic() - run_match_start, 0)
        )
        logging.info('match %s: done', match_id)

        @retry(
            reraise=True,
            stop=stop_after_attempt(15),
            wait=wait_fixed(10),
            retry=retry_if_exception_type(socket.error),
        )
        async def send_master_result():
            await self.master.match_done(
                self.get_worker_infos(),
                match_id,
                result,
            )

        try:
            await send_master_result()
        except socket.error:
            logging.warning(
                'master down, cannot send match %s result', match_id
            )
        else:
            logging.info('match %s: sent to masternode', match_id)
