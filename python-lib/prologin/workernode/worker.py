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
import itertools
import logging
import logging.handlers
import os
import os.path
import prologin.rpc.client
import prologin.rpc.server
import re
import socket
import sys
import tempfile
import time
import tornado
import tornado.platform.asyncio
import yaml

from base64 import b64decode, b64encode
from . import operations

from .monitoring import (
    workernode_slots,
    workernode_compile_champion_summary,
    workernode_run_match_summary)

tornado.platform.asyncio.AsyncIOMainLoop().install()

def async_work(func=None, slots=0):
    if func is None:
        return functools.partial(async_work, slots=slots)
    @functools.wraps(func)
    def mktask(self, *args, **kwargs):
        @asyncio.coroutine
        def wrapper(self, *wargs, **wkwargs):
            if self.slots < slots:
                logging.warn('not enough slots to start the required job')
                return
            logging.debug('starting a job for {} slots'.format(slots))
            self.slots -= slots
            workernode_slots.set(self.slots)
            yield from self.update_master()
            try:
                r = yield from func(self, *wargs, **wkwargs)
            finally:
                self.slots += slots
                workernode_slots.set(self.slots)
                yield from self.update_master()
        asyncio.Task(wrapper(self, *args, **kwargs), loop=self.loop)
        return slots
    return mktask


class WorkerNode(prologin.rpc.server.BaseRPCApp):
    def __init__(self, *args, config=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.interval = config['master']['heartbeat_secs']
        self.hostname = socket.gethostname()
        self.port = config['worker']['port']
        self.slots = self.max_slots = config['worker']['available_slots']
        self.matches = {}
        self.loop = asyncio.get_event_loop()
        self.master = self.get_master()

    def run(self):
        logging.info('worker listening on {}'.format(
            self.config['worker']['port']))
        self.listen(self.config['worker']['port'])
        asyncio.Task(self.send_heartbeat())
        self.loop.run_forever()

    def stop(self):
        self.loop.stop()

    def get_worker_infos(self):
        return (self.hostname, self.port, self.slots, self.max_slots)

    def get_master(self):
        config = self.config
        host, port = (config['master']['host'], config['master']['port'])
        url = "http://{}:{}/".format(host, port)
        return prologin.rpc.client.Client(url,
                secret=config['master']['shared_secret'].encode('utf-8'),
                coro=True)

    @asyncio.coroutine
    def update_master(self):
        try:
            yield from self.master.update_worker(self.get_worker_infos())
        except socket.error:
            logging.warn('master down, cannot update it')

    @asyncio.coroutine
    def send_heartbeat(self):
        logging.debug('sending heartbeat to the server, {}/{} slots'.format(
            self.slots, self.max_slots))
        first_heartbeat = True
        while True:
            try:
                yield from self.master.heartbeat(self.get_worker_infos(),
                                                 first_heartbeat)
                first_heartbeat = False
            except socket.error:
                logging.warn('master down, retrying heartbeat in {}s'.format(
                        self.interval))

            yield from asyncio.sleep(self.interval)

    @prologin.rpc.remote_method
    def reachable(self):
        return True

    @prologin.rpc.remote_method
    @async_work(slots=1)
    def compile_champion(self, user, cid, ctgz):
        compile_champion_start = time.monotonic()

        ctgz = b64decode(ctgz)

        with tempfile.TemporaryDirectory() as cpath:
            compiled_path = os.path.join(cpath, 'champion-compiled.tar.gz')
            log_path = os.path.join(cpath, 'compilation.log')

            with open(os.path.join(cpath, 'champion.tgz'), 'wb') as f:
                f.write(ctgz)

            ret = yield from operations.compile_champion(self.config, cpath)

            compilation_content = b''
            log = ''
            if ret:
                try:
                    with open(compiled_path, 'rb') as f:
                        compilation_content = f.read()
                except FileNotFoundError:
                    ret = False
            try:
                with open(log_path, 'r') as f:
                    log = f.read()
            except FileNotFoundError:
                pass

        b64compiled = b64encode(compilation_content).decode()
        try:
            yield from self.master.compilation_result(self.get_worker_infos(),
                    cid, user, ret, b64compiled, log,
                    max_retries=self.config['master']['max_retries'],
                    retry_delay=self.config['master']['retry_delay'])
        except socket.error:
            logging.warning('master down, cannot send compiled {}'.format(
                cid))

        workernode_compile_champion_summary.observe(
            max(time.monotonic() - compile_champion_start, 0))

    @prologin.rpc.remote_method
    @async_work(slots=5)
    def run_match(self, match_id, players, opts=None, file_opts=None):
        logging.info('starting match {}'.format(match_id))
        run_match_start = time.monotonic()

        socket_dir = tempfile.TemporaryDirectory(prefix='workernode-')
        os.chmod(socket_dir.name, 0o777)
        f_reqrep = socket_dir.name + '/' + 'reqrep'
        f_pubsub = socket_dir.name + '/' + 'pubsub'
        s_reqrep = 'ipc://' + f_reqrep
        s_pubsub = 'ipc://' + f_pubsub

        opts = list(itertools.chain(opts.items()))

        # Server
        task_server = asyncio.Task(operations.spawn_server(self.config,
            s_reqrep, s_pubsub, len(players), opts, file_opts))
        yield from asyncio.sleep(0.1) # Let the server start

        for i in range(5):
            try:
                os.chmod(f_reqrep, 0o777)
                os.chmod(f_pubsub, 0o777)
                break
            except FileNotFoundError:
                yield from asyncio.sleep(1)
        else:
            logging.error("Server socket was never created")
            return

        # Dumper
        task_dumper = asyncio.Task(operations.spawn_dumper(self.config,
            s_reqrep, s_pubsub, opts, file_opts))

        # Players
        tasks_players = {}
        champion_dirs = []
        for pl_id, (c_id, ctgz) in players.items():
            ctgz = b64decode(ctgz)
            cdir = tempfile.TemporaryDirectory()
            champion_dirs.append(cdir)
            yield from self.loop.run_in_executor(None, operations.untar,
                                                 ctgz, cdir.name)
            tasks_players[pl_id] = asyncio.Task(operations.spawn_client(
                self.config, s_reqrep, s_pubsub, pl_id, cdir.name,
                socket_dir.name, opts, file_opts))

        # Wait for the match to complete
        yield from asyncio.wait([task_server, task_dumper] +
                                list(tasks_players.values()))
        logging.info('match {} done'.format(match_id))

        # Get the output of the tasks
        server_stdout = task_server.result()
        dumper_stdout = b64encode(task_dumper.result()).decode()
        players_stdout = {pl_id: (players[pl_id][0], # champion_id
                                  b64encode(t.result()[1]).decode()) # output
                          for pl_id, t in tasks_players.items()}

        # Extract the match result from the server stdout
        # stechec2 rules can output non-dict data, discard it
        server_result = yaml.safe_load_all(server_stdout)
        server_result = [r for r in server_result if isinstance(r, dict)]

        # Remove the champion temporary directories
        for tmpdir in champion_dirs:
            tmpdir.cleanup()
        socket_dir.cleanup()

        try:
            yield from self.master.match_done(self.get_worker_infos(),
                    match_id, server_result, dumper_stdout, server_stdout,
                    players_stdout,
                    max_retries=self.config['master']['max_retries'],
                    retry_delay=self.config['master']['retry_delay'])
        except socket.error:
            logging.warning('master down, cannot send match {} result'.format(
                match_id))

        workernode_run_match_summary.observe(
            max(time.monotonic() - run_match_start, 0))
