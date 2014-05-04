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
import copy
import logging
import optparse
import os.path
import prologin.config
import prologin.log
import prologin.rpc.server
import psycopg2
import psycopg2.extras
import random
import time

from .worker import Worker
from .concoursquery import ConcoursQuery
from . import task

loop = asyncio.get_event_loop()
tornado.platform.asyncio.AsyncIOMainLoop().install()

class MasterNode(prologin.rpc.server.BaseRPCApp):
    def __init__(self, *args, config=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.workers = {}
        self.worker_tasks = []
        self.matches = {}
        self.db = ConcoursQuery(config)

        self.spawn_tasks()

    def spawn_tasks(self):
        self.to_dispatch = asyncio.Event()
        self.janitor = asyncio.Task(self.janitor_task())
        self.dbwatcher = asyncio.Task(self.dbwatcher_task())
        self.dispatcher = asyncio.Task(self.dispatcher_task())

    @prologin.rpc.remote_method
    def status(self):
        d = []
        for (host, port), w in self.workers.items():
            d.append((host, port, w.slots, w.max_slots))
        return d

    @prologin.rpc.remote_method
    def update_worker(self, worker):
        hostname, port, slots, max_slots = worker
        key = hostname, port
        if key not in self.workers:
            logging.warn("registered new worker: {}:{}".format(hostname, port))
            self.workers[key] = Worker(hostname, port, slots, max_slots,
                    self.config)
        else:
            logging.debug("updating worker: {}:{} {}/{}".format(
                              hostname, port, slots, max_slots))
            self.workers[key].update(slots, max_slots)

    @prologin.rpc.remote_method
    def heartbeat(self, worker, first):
        hostname, port, slots, max_slots = worker
        usage = (1.0 - float(slots) / max_slots) * 100
        logging.info('received heartbeat from {}:{}, usage is {:.2%}'.format(
                         hostname, port, usage))
        if first and (hostname, port) in self.workers:
            self.redispatch_worker(self.workers[(hostname, port)])
        self.update_worker(worker)

    @prologin.rpc.remote_method
    def compilation_result(self, worker, champ_id, ret):
        hostname, port, slots, max_slots = worker
        w = self.workers[(hostname, port)]
        w.remove_compilation_task(champ_id)
        loop.add_callback(self.complete_compilation, champ_id, ret)

    def complete_compilation(self, champ_id, ret):
        if ret is True:
            status = 'ready'
        else:
            status = 'error'

        logging.info('compilation of champion {}: {}'.format(champ_id, status))
        self.db.execute('set_champion_status', champion_id=champ_id,
                champion_stats=status)

    @prologin.rpc.remote_method
    def match_done(self, mid, result):
        logging.info('match {} ended'.format(mid))

        @asyncio.coroutine
        def match_done_db(mid, result):
            yield from self.db.execute('set_match_status',
                    { 'match_id': mid, 'match_status': 'done' })

            t = [{ 'player_id': r[0], 'player_score': r[1]}
                    for r in result]
            yield from self.db.execute_many('set_player_score', t)

            t = [{ 'match_id': mid, 'champion_score': r[1], 'player_id': r[0]}
                    for r in result]
            yield from self.db.execute_many('update_tournament_score', t)

        asyncio.Task(match_done_db(mid, result))
        self.workers[(worker[0], worker[1])].remove_match_task(mid)

    @prologin.rpc.remote_method
    def client_done(self, worker, mpid):
        self.workers[(worker[0], worker[1])].remove_player_task(mpid)

    def redispatch_worker(self, worker):
        tasks = [t for (t, g) in worker.tasks]
        if tasks:
            logging.info("redispatching tasks for {}: {}".format(
                             worker, tasks))
            self.worker_tasks = tasks + self.worker_tasks
            self.to_dispatch.set()
        del self.workers[(worker.hostname, worker.port)]

    @asyncio.coroutine
    def janitor_task(self):
        while True:
            all_workers = copy.copy(self.workers)
            for worker in all_workers.values():
                if not worker.is_alive(self.config['worker']['timeout_secs']):
                    logging.warn("timeout detected for worker {}".format(
                                worker))
                    self.redispatch_worker(worker)
            yield from asyncio.sleep(1)

    @asyncio.coroutine
    def check_requested_compilations(self, status='new'):
        to_set_pending = []
        yield from self.db.execute('get_champions',
            { 'champion_status': status })

        for r in cur:
            logging.info('requested compilation for {} / {}'.format(
                              r['name'], r['id']))
            to_set_pending.append({
                'champion_id': r['id'],
                'champion_status': 'pending'
            })
            t = task.CompilationTask(self.config, r['name'], r['id'])
            self.worker_tasks.append(t)

        if to_set_pending:
            self.to_dispatch.set()
        yield from self.db.executemany('set_champion_status', to_set_pending)

    @asyncio.coroutine
    def check_requested_matches(self, status='new'):
        to_set_pending = []
        c = yield from self.db.execute('get_matches', {'match_status': status})

        for r in c:
            logging.info('request match id {} launch'.format(r['match_id']))
            mid = r['match_id']
            opts = r['match_options']
            players = list(zip(r['champion_ids'], r['match_player_ids'],
                          r['user_names']))
            to_set_pending.append({
                'match_id': mid,
                'match_status': 'pending',
            })
            t = task.MatchTask(self.config, mid, players, opts)
            self.worker_tasks.append(t)

        if to_set_pending:
            self.to_dispatch.set()
        yield from self.db.executemany('set_match_status', to_set_pending)

    @asyncio.coroutine
    def dbwatcher_task(self):
        self.check_requested_compilations('pending')
        self.check_requested_matches('pending')
        while True:
            self.check_requested_compilations()
            self.check_requested_matches()
            yield from asyncio.sleep(1)

    def find_worker_for(self, task):
        available = list(self.workers.values())
        available = [w for w in available if w.can_add_task(task)]
        random.shuffle(available)
        available.sort(key=lambda w: w.usage)
        if not available:
            return None
        else:
            return available[0]

    @asyncio.coroutine
    def dispatcher_task(self):
        while True:
            yield from self.to_dispatch.wait()
            if self.worker_tasks:
                task = self.worker_tasks[0]
                w = self.find_worker_for(task)
                if w is None:
                    logging.info("no worker available for task {}".format(task))
                else:
                    w.add_task(self, task)
                    logging.debug("task {} got to {}".format(task, w))
                    self.worker_tasks = self.worker_tasks[1:]
            if not self.worker_tasks:
                self.to_dispatch.clear()
            yield from asyncio.sleep(0.1) # Avoid blocking with lot of dispatch


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-l', '--local-logging', action='store_true',
                      dest='local_logging', default=False,
                      help='Activate logging to stdout.')
    parser.add_option('-v', '--verbose', action='store_true',
                      dest='verbose', default=False,
                      help='Verbose mode.')
    options, args = parser.parse_args()

    prologin.log.setup_logging('masternode', verbose=options.verbose,
                               local=options.local_logging)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    config = prologin.config.load('masternode')

    s = MasterNode(config=config, app_name='masternode',
                   secret=config['master']['shared_secret'].encode('utf-8'))
    s.listen(config['master']['port'])

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass