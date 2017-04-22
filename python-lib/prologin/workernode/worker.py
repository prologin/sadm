# This file is part of Prologin-SADM.
#
# Copyright (c) 2013-2015 Antoine Pietri <antoine.pietri@prologin.org>
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

from . import operations

from .monitoring import (
    workernode_slots,
    workernode_compile_champion_summary,
    workernode_run_match_summary)


def async_work(func=None, slots=0):
    if func is None:
        return functools.partial(async_work, slots=slots)

    @functools.wraps(func)
    async def mktask(self, *args, **kwargs):
        async def wrapper(self, *wargs, **wkwargs):
            if self.slots < slots:
                logging.warn('not enough slots to start the required job')
                return
            logging.debug('starting a job for {} slots'.format(slots))
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
        logging.info('worker listening on {}'
                     .format(self.config['worker']['port']))
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
            url, secret=config['master']['shared_secret'].encode('utf-8'))

    async def update_master(self):
        try:
            await self.master.update_worker(self.get_worker_infos())
        except socket.error:
            logging.warn('master down, cannot update it')

    async def send_heartbeat(self):
        logging.debug('sending heartbeat to the server, {}/{} slots'
                      .format(self.slots, self.max_slots))
        first_heartbeat = True
        while True:
            try:
                await self.master.heartbeat(self.get_worker_infos(),
                                            first_heartbeat)
                first_heartbeat = False
            except socket.error:
                logging.warn('master down, retrying heartbeat in {}s'
                             .format(self.interval))

            await asyncio.sleep(self.interval)

    @prologin.rpc.remote_method
    async def reachable(self):
        return True

    @prologin.rpc.remote_method
    @async_work(slots=1)
    async def compile_champion(self, user, cid, ctgz):
        compile_champion_start = time.monotonic()

        ret, compiled, log = await operations.compile_champion(self.config,
                                                               ctgz)
        try:
            await self.master.compilation_result(
                self.get_worker_infos(),
                cid, user, ret, compiled, log,
                max_retries=self.config['master']['max_retries'],
                retry_delay=self.config['master']['retry_delay'])
        except socket.error:
            logging.warning('master down, cannot send compiled {}'.format(
                cid))

        workernode_compile_champion_summary.observe(
            max(time.monotonic() - compile_champion_start, 0))

    @prologin.rpc.remote_method
    @async_work(slots=5)
    async def run_match(self, match_id, players, opts=None, file_opts=None):
        logging.info('starting match {}'.format(match_id))
        run_match_start = time.monotonic()

        server_result, server_out, dump, players_info = await (
            operations.spawn_match(self.config, players, opts, file_opts))
        logging.info('match {} done'.format(match_id))

        try:
            await self.master.match_done(
                self.get_worker_infos(),
                match_id, server_result, dump, server_out, players_info,
                max_retries=self.config['master']['max_retries'],
                retry_delay=self.config['master']['retry_delay'])
        except socket.error:
            logging.warning('master down, cannot send match {} result'.format(
                match_id))

        workernode_run_match_summary.observe(
            max(time.monotonic() - run_match_start, 0))
