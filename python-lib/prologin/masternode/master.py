# -*- encoding: utf-8 -*-
# This file is part of Prologin-SADM.
#
# Copyright (c) 2013-2015 Antoine Pietri <antoine.pietri@prologin.org>
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
import json
import logging
import os.path
import prologin.rpc.server
import random
import time

from base64 import b64decode, b64encode

from .concoursquery import ConcoursQuery
from .monitoring import (
    masternode_bad_result,
    masternode_client_done_file,
    masternode_match_done_db,
    masternode_match_done_file,
    masternode_request_compilation_task,
    masternode_task_redispatch,
    masternode_worker_timeout,
)
from .task import MatchTask, CompilationTask
from .task import champion_compiled_path, match_path, clog_path
from .worker import Worker


class MasterNode(prologin.rpc.server.BaseRPCApp):
    def __init__(self, *args, config=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.workers = {}
        self.worker_tasks = []
        self.db = ConcoursQuery(config)

    def run(self):
        logging.info('master listening on %s', self.config['master']['port'])
        self.to_dispatch = asyncio.Event()
        self.janitor = asyncio.Task(self.janitor_task())
        self.dbwatcher = asyncio.Task(self.dbwatcher_task())
        self.dispatcher = asyncio.Task(self.dispatcher_task())
        super().run(port=self.config['master']['port'])

    @prologin.rpc.remote_method
    async def status(self):
        d = []
        for (host, port), w in self.workers.items():
            d.append((host, port, w.slots, w.max_slots))
        return d

    async def register_worker(self, key, w):
        if (await w.reachable()):
            logging.warning("registered new worker: %s:%s", w.hostname, w.port)
            self.workers[key] = w
        else:
            logging.warning("drop unreachable worker: %s:%s",
                            w.hostname, w.port)

    @prologin.rpc.remote_method
    async def update_worker(self, worker):
        hostname, port, slots, max_slots = worker
        key = hostname, port
        if key not in self.workers:
            w = Worker(hostname, port, slots, max_slots, self.config)
            await self.register_worker(key, w)
        else:
            logging.debug("updating worker: %s:%s %s/%s",
                          hostname, port, slots, max_slots)
            self.workers[key].update(slots, max_slots)

    @prologin.rpc.remote_method
    async def heartbeat(self, worker, first):
        hostname, port, slots, max_slots = worker
        usage = (1.0 - slots / max_slots)
        logging.debug('received heartbeat from %s:%s, usage is %.2f%%',
                      hostname, port, usage * 100)
        if first and (hostname, port) in self.workers:
            self.redispatch_worker(self.workers[(hostname, port)])
        await self.update_worker(worker)

    @prologin.rpc.remote_method
    async def compilation_result(self, worker, cid, user, ret, b64compiled,
                                 log):
        hostname, port, slots, max_slots = worker
        w = self.workers[(hostname, port)]

        # Ignore the tasks we already redispatched
        if w.get_compilation_task(cid) is None:
            return

        w.remove_compilation_task(cid)
        status = 'ready' if ret else 'error'
        if ret:
            with open(champion_compiled_path(self.config, user, cid),
                      'wb') as f:
                f.write(b64decode(b64compiled))
        with open(clog_path(self.config, user, cid), 'w') as f:
            f.write(log)
        logging.info('compilation of champion %s: %s', cid, status)
        await self.db.execute(
            'set_champion_status',
            {'champion_id': cid, 'champion_status': status})

    @prologin.rpc.remote_method
    async def match_done(self, worker, mid, result, dumper_stdout,
                         server_stdout, players_stdout):
        hostname, port, slots, max_slots = worker
        w = self.workers[(hostname, port)]

        # Ignore the tasks we already redispatched
        if w.get_match_task(mid) is None:
            return

        logging.info('match %s ended', mid)

        # Write player logs
        for pl_id, (champ_id, retcode, log) in players_stdout.items():
            logname = 'log-champ-{}-{}.log'.format(pl_id, champ_id)
            logpath = os.path.join(match_path(self.config, mid), logname)
            with masternode_client_done_file.time(), \
                open(logpath, 'w') as fplayer:
                fplayer.write(log)

        # Write server logs and dumper log
        serverpath = os.path.join(match_path(self.config, mid), 'server.log')
        dumppath = os.path.join(match_path(self.config, mid), 'dump.json.gz')
        with masternode_match_done_file.time(), \
             open(serverpath, 'w') as fserver, \
             open(dumppath, 'wb') as fdump:
            fserver.write(server_stdout)
            fdump.write(b64decode(dumper_stdout))

        try:
            match_status = {'match_id': mid, 'match_status': 'done'}
            player_scores = [{'player_id': r['player'],
                              'player_score': r['score']}
                             for r in result]
            tournament_scores = [{'match_id': mid,
                                  'champion_score': r['score'],
                                  'player_id': r['player']}
                                 for r in result]
        except KeyError:
            masternode_bad_result.inc()
            return

        start = time.monotonic()
        await self.db.execute('set_match_status', match_status)
        await self.db.executemany('set_player_score', player_scores)
        await self.db.executemany('update_tournament_score', tournament_scores)
        masternode_match_done_db.observe(time.monotonic() - start)

        # Remove task from worker
        w.remove_match_task(mid)

    def redispatch_worker(self, worker):
        masternode_task_redispatch.inc(len(worker.tasks))
        if worker.tasks:
            logging.info("redispatching tasks for %s: %s", worker, worker.tasks)
            self.worker_tasks = worker.tasks + self.worker_tasks
            self.to_dispatch.set()
        del self.workers[(worker.hostname, worker.port)]

    def redispatch_timeout_tasks(self, worker):
        for i, t in list(enumerate(worker.tasks)):
            if t.has_timeout():
                worker.tasks.pop(i)
                max_tries = self.config['worker']['max_task_tries']
                if t.executions < max_tries:
                    self.worker_tasks.append(t)
                    self.to_dispatch.set()
                    msg = "redispatching (try {}/{})".format(t.executions,
                                                             max_tries)
                else:
                    msg = "maximum number of retries exceeded, bailing out"
                logging.info("task %s of %s timeout: %s", t, worker, msg)

    async def janitor_task(self):
        while True:
            try:
                for worker in list(self.workers.values()):
                    if not worker.is_alive(
                            self.config['worker']['timeout_secs']):
                        masternode_worker_timeout.inc()
                        logging.warning("timeout detected for worker %s",
                                        worker)
                        self.redispatch_worker(worker)
                    self.redispatch_timeout_tasks(worker)
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception('Janitor task triggered an exception')
            await asyncio.sleep(1)

    async def check_requested_compilations(self, status='new'):
        to_set_pending = []
        res = await self.db.execute('get_champions',
                                    {'champion_status': status})

        for r in res:
            logging.info('requested compilation for %s / %s', r[1], r[0])
            masternode_request_compilation_task.inc()
            to_set_pending.append({
                'champion_id': r[0],
                'champion_status': 'pending'
            })
            t = CompilationTask(self.config, r[1], r[0])
            self.worker_tasks.append(t)

        if to_set_pending:
            self.to_dispatch.set()
        await self.db.executemany('set_champion_status', to_set_pending)

    async def check_requested_matches(self, status='new'):
        to_set_pending = []
        c = await self.db.execute('get_matches', {'match_status': status})
        for r in c:
            logging.info('request match id %s launch', r[0])
            mid = r[0]
            opts_json = r[1]
            file_opts_json = r[2]
            players = list(zip(r[3], r[4], r[5]))

            opts = {}
            if opts_json:
                try:
                    opts = json.loads(opts_json)
                except (TypeError, ValueError):
                    logging.warning('cannot decode the custom options json,'
                                    'assuming it is empty', exc_info=1)

            file_opts = {}
            if file_opts_json:
                try:
                    file_opts_paths = json.loads(file_opts_json)
                except (TypeError, ValueError):
                    logging.warning('cannot decode the custom options json,'
                                    'assuming it is empty', exc_info=1)
            for k, path in file_opts_paths.items():
                try:
                    file_opts[k] = b64encode(open(path, 'rb').read()).decode()
                except FileNotFoundError:
                    logging.warning('file for option %s not found: %s', k, path)

            to_set_pending.append({
                'match_id': mid,
                'match_status': 'pending',
            })
            try:
                t = MatchTask(self.config, mid, players, opts, file_opts)
                self.worker_tasks.append(t)
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception('Unable to create task for match %s', mid)

        if to_set_pending:
            self.to_dispatch.set()
        await self.db.executemany('set_match_status', to_set_pending)

    async def dbwatcher_task(self):
        while True:
            try:
                await self.check_requested_compilations('pending')
                await self.check_requested_matches('pending')
                while True:
                    await self.check_requested_compilations()
                    await self.check_requested_matches()
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception('DB Watcher task triggered an exception')
                await asyncio.sleep(5)
                continue

    def find_worker_for(self, task):
        available = list(self.workers.values())
        available = [w for w in available if w.can_add_task(task)]
        random.shuffle(available)
        available.sort(key=lambda w: w.usage)
        if not available:
            return None
        else:
            return available[0]

    async def dispatcher_task(self):
        while True:
            try:
                logging.info('Dispatcher task: %d tasks in queue',
                             len(self.worker_tasks))
                await self.to_dispatch.wait()

                # Try to schedule up to 25 tasks. The throttling is in place to
                # avoid potential overload.
                for i in range(25):
                    if not self.worker_tasks:
                        break
                    task = self.worker_tasks[0]
                    w = self.find_worker_for(task)
                    if w is None:
                        logging.info("no worker available for task %s", task)
                        break
                    else:
                        w.add_task(self, task)
                        logging.debug("task %s got to %s", task, w)
                        self.worker_tasks = self.worker_tasks[1:]
                if not self.worker_tasks:
                    self.to_dispatch.clear()
                else:
                    await asyncio.sleep(1)  # No worker available, wait 1s

                # Give the hand back to the event loop to avoid being blocking,
                # but be called as soon as all the functions at the top of the
                # heap have been executed
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception('Dispatcher task triggered an exception')
                await asyncio.sleep(3)
                continue
