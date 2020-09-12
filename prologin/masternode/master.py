# -*- encoding: utf-8 -*-
# This file is part of Prologin-SADM.
#
# Copyright (c) 2013-2020 Antoine Pietri <antoine.pietri@prologin.org>
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
import prologin.rpc.server
import random
import time

from base64 import b64decode

from .concoursquery import ConcoursQuery
from .monitoring import (
    masternode_bad_result,
    masternode_client_done_file,
    masternode_match_done_db,
    masternode_match_done_file,
    masternode_request_compilation_task,
    masternode_task_dispatch,
    masternode_task_redispatch,
    masternode_task_resubmit,
    masternode_task_fail,
    masternode_worker_timeout,
    masternode_zombie_worker,
    masternode_exception,
)
from .task import (
    CompilationTask,
    MatchTask,
    get_champion_dir,
    get_match_dir,
)
from .worker import Worker


class MasterNode(prologin.rpc.server.BaseRPCApp):
    def __init__(self, *args, config=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.workers = {}
        self.db = ConcoursQuery(config)

    def run(self):
        logging.info("master listening on %s", self.config["master"]["port"])
        self.janitor = asyncio.Task(self.janitor_task())
        self.dbwatcher_compilations = asyncio.Task(
            self.dbwatcher_task("compilation", self.get_requested_compilations)
        )
        self.dbwatcher_matches = asyncio.Task(
            self.dbwatcher_task("matches", self.get_requested_matches)
        )
        super().run(port=self.config["master"]["port"])

    @prologin.rpc.remote_method
    async def status(self):
        d = []
        for (host, port), w in self.workers.items():
            d.append((host, port, w.slots, w.max_slots))
        return d

    async def register_worker(self, key, w):
        if await w.reachable():
            logging.warning("registered new worker: %s:%s", w.hostname, w.port)
            self.workers[key] = w
        else:
            logging.warning(
                "dropped unreachable worker: %s:%s", w.hostname, w.port
            )

    @prologin.rpc.remote_method
    async def update_worker(self, worker):
        hostname, port, slots, max_slots = worker
        key = hostname, port
        if key not in self.workers:
            w = Worker(hostname, port, slots, max_slots, self.config)
            await self.register_worker(key, w)
        else:
            logging.debug(
                "updating worker: %s:%s %s/%s",
                hostname,
                port,
                slots,
                max_slots,
            )
            self.workers[key].update(slots, max_slots)

    @prologin.rpc.remote_method
    async def heartbeat(self, worker, first):
        hostname, port, slots, max_slots = worker
        usage = 1.0 - slots / max_slots
        logging.debug(
            'received heartbeat from %s:%s, usage is %.2f%%',
            hostname,
            port,
            usage * 100,
        )
        if first and (hostname, port) in self.workers:
            await self.redispatch_worker(self.workers[(hostname, port)])
        await self.update_worker(worker)

    @prologin.rpc.remote_method
    async def compilation_done(self, worker, user, champion_id, result):
        hostname, port, slots, max_slots = worker
        try:
            w = self.workers[(hostname, port)]
        except KeyError:
            # Ignore tasks from zombie workers
            masternode_zombie_worker.inc()
            logging.info(
                'discarding result from zombie worker %s',
                str((hostname, port)),
            )
            return

        task = w.get_compilation_task(champion_id)
        # Ignore the tasks we already redispatched
        if task is None:
            logging.info(
                'discarding result of redispatched compilation task %s',
                champion_id,
            )
            return
        w.remove_compilation_task(task)

        if result['success']:  # Successful compilation
            status = 'ready'
        elif 'error' in result:  # Internal error
            status = 'failed'
        else:  # Compilation failure
            status = 'error'
        logging.info('compilation of champion %s: %s', champion_id, status)

        champion_path = get_champion_dir(self.config, user, champion_id)
        if result['stdout'] is not None:
            (champion_path / 'compilation.log').write_text(result['stdout'])
        if result['success'] and result['champion_compiled']:
            (champion_path / 'champion-compiled.tgz').write_bytes(
                b64decode(result['champion_compiled'])
            )
        (champion_path / 'compilation-workernode-result.json').write_text(
            json.dumps(result)
        )
        await self.db.execute(
            'set_champion_status',
            {'champion_id': champion_id, 'champion_status': status},
        )

    @prologin.rpc.remote_method
    async def match_done(self, worker, mid, result):
        hostname, port, slots, max_slots = worker
        try:
            w = self.workers[(hostname, port)]
        except KeyError:
            # Ignore tasks from zombie workers
            masternode_zombie_worker.inc()
            logging.info(
                'discarding result zombie worker %s', str((hostname, port))
            )
            return

        task = w.get_match_task(mid)
        # Ignore the tasks we already redispatched
        if task is None:
            logging.info(
                'discarding result of redispatched match task %s', mid
            )
            return
        w.remove_match_task(task)

        if result['success']:
            status = 'done'
        else:
            status = 'failed'
        logging.info('result of match %s: %s', mid, status)
        match_path = get_match_dir(self.config, mid)

        # Write player logs
        for player_id, player_result in result['players'].items():
            logname = 'log-champ-{}-{}.log'.format(
                player_id, player_result['champion_id']
            )
            with masternode_client_done_file.time():
                if player_result['stdout'] is not None:
                    (match_path / logname).write_text(player_result['stdout'])

        # Store match artifacts
        with masternode_match_done_file.time():
            if result['stdout'] is not None:
                (match_path / 'server.stdout.log').write_text(result['stdout'])
            if result['stderr'] is not None:
                (match_path / 'server.stderr.log').write_text(result['stderr'])
            if result['dump']:
                (match_path / 'dump.json.gz').write_bytes(
                    b64decode(result['dump'])
                )
            if result['replay']:
                (match_path / 'replay.gz').write_bytes(
                    b64decode(result['replay'])
                )
            if result['stats']:
                (match_path / 'server_stats.yaml.gz').write_bytes(
                    b64decode(result['stats'])
                )
            (match_path / 'server-workernode-result.json').write_text(
                json.dumps(result)
            )

        start = time.monotonic()
        if status == 'done':
            try:
                player_scores = [
                    {
                        'player_id': r['player'],
                        'player_score': r['score'],
                        'player_timeout': r['nb_timeout'] != 0,
                    }
                    for r in result['match_result']
                ]
            except KeyError:
                masternode_bad_result.inc()
                logging.warning(
                    "received malformed result for match result %s: %s",
                    mid,
                    repr(result['match_result']),
                )
                status = 'failed'
            else:
                await self.db.executemany('set_player_score', player_scores)

        match_status = {'match_id': mid, 'match_status': status}
        await self.db.execute('set_match_status', match_status)
        masternode_match_done_db.observe(time.monotonic() - start)

    async def redispatch_worker(self, worker):
        masternode_task_redispatch.inc(len(worker.tasks))

        if worker.tasks:
            logging.info(
                "redispatching tasks for %s: %s", worker, worker.tasks
            )
            for task in worker.tasks.copy():
                asyncio.create_task(task.redispatch())

        del self.workers[(worker.hostname, worker.port)]

    async def resubmit_timeout_tasks(self, worker):
        tasks_to_fail = set()
        for t in worker.tasks.copy():
            if t.has_timeout() or t.has_error():
                max_tries = self.config["worker"]["max_task_tries"]
                error_msg = f' last error: {t.error}' if t.has_error() else ''
                if t.executions < max_tries:
                    msg = (
                        "resubmitted (try {}/{})".format(
                            t.executions, max_tries
                        )
                        + error_msg
                    )
                    masternode_task_resubmit.inc()
                    asyncio.create_task(t.execute(self, worker))
                else:
                    msg = (
                        "maximum number of retries exceeded, failing task"
                        + error_msg
                    )
                    tasks_to_fail.add(t)
                logging.info("task %s of %s timeout: %s", t, worker, msg)

        masternode_task_fail.inc(len(tasks_to_fail))
        for task in tasks_to_fail:
            worker.tasks.discard(task)
            asyncio.create_task(task.fail())

    async def janitor_task(self):
        while True:
            try:
                for worker in list(self.workers.values()):
                    if not worker.is_alive(
                        self.config['worker']['timeout_secs']
                    ):
                        masternode_worker_timeout.inc()
                        logging.warning(
                            "timeout detected for worker %s", worker
                        )
                        await self.redispatch_worker(worker)
                    await self.resubmit_timeout_tasks(worker)
            except asyncio.CancelledError:
                raise
            except Exception:
                masternode_exception.inc()
                logging.exception('Janitor task triggered an exception')
            await asyncio.sleep(1)

    async def get_requested_compilations(self, status="new"):
        rows = await self.db.execute(
            "get_champions", {"champion_status": status}
        )

        tasks = [
            CompilationTask(self.config, self.db, username, champion_id)
            for champion_id, username in rows
        ]

        return tasks

    async def get_requested_matches(self, status="new"):
        rows = await self.db.execute("get_matches", {"match_status": status})

        tasks = []
        for (
            match_id,
            map_contents,
            champion_ids,
            player_ids,
            usernames,
        ) in rows:
            players = list(zip(champion_ids, player_ids, usernames))
            try:
                t = MatchTask(
                    self.config, self.db, match_id, players, map_contents
                )
                tasks.append(t)
            except asyncio.CancelledError:
                raise
            except Exception:
                masternode_exception.inc()
                logging.exception(
                    'Unable to create task for match %s', match_id
                )

        return tasks

    async def dbwatcher_task(self, name, fetcher):
        while True:
            try:
                # Redispatch pending tasks from previous masternode
                tasks = await fetcher("pending")
                if tasks:
                    await asyncio.wait([task.redispatch() for task in tasks])

                while True:
                    tasks = await fetcher()
                    if tasks:
                        await self.dispatch_tasks(name, tasks)
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception:
                masternode_exception.inc()
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

    async def dispatch_tasks(self, queue_name, tasks):
        logging.info("%d tasks in %s queue", len(tasks), queue_name)

        coros = []
        for task in tasks:
            w = self.find_worker_for(task)
            if w is None:
                logging.info("no worker available for task %s", task)
                # It's okay to break the loop because all the items in the task
                # queue are expected to have the same requirements, hence if
                # one task cannot be scheduled then none of the others will.
                break
            masternode_task_dispatch.inc()
            try:
                coros.append(w.add_task(self, task))
                logging.debug("task %s sent to %s", task, w)
            except Exception:
                masternode_exception.inc()
                logging.exception('Could not dispatch task %s to %s', task, w)

        # Ensure the tasks are scheduled (=set as pending).
        if coros:
            await asyncio.wait(coros)
