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

from .worker import Worker

import copy
import logging
import logging.handlers
import optparse
import os.path
import prologin.config
import prologin.log
import prologin.rpc.server
import psycopg2
import psycopg2.extras
import random
from . import task
import tornado
import tornado.ioloop
import tornado.gen
import utils

utils.init_psycopg_tornado()
ioloop = tornado.ioloop.IOLoop.instance()

class MasterNode:
    def __init__(self, config):
        self.config = config
        self.workers = {}
        self.worker_tasks = []
        self.matches = {}

        self.spawn_tasks()

    def spawn_tasks(self):
        self.janitor = ioloop.add_callback(self.janitor_task)
        self.dbwatcher = ioloop.add_callback(self.dbwatcher_task)
        self.dispatcher = ioloop.add_callback(self.dispatcher_task)

    @property
    def status(self):
        d = []
        for (host, port), w in self.workers.items():
            d.append((host, port, w.slots, w.max_slots))
        return d

    def update_worker(self, worker):
        hostname, port, slots, max_slots = worker
        key = hostname, port
        if key not in self.workers:
            logging.warn("registered new worker: %s:%d" % (hostname, port))
            self.workers[key] = Worker(hostname, port, slots, max_slots,
                    self.config)
        else:
            logging.debug("updating worker: %s:%d %d/%d" % (
                              hostname, port, slots, max_slots
                         ))
            self.workers[key].update(slots, max_slots)

    def heartbeat(self, worker, first):
        hostname, port, slots, max_slots = worker
        usage = (1.0 - float(slots) / max_slots) * 100
        logging.info('received heartbeat from %s:%d, usage is %.2f%%' % (
                         hostname, port, usage
                    ))
        if first and (hostname, port) in self.workers:
            self.redispatch_worker(self.workers[(hostname, port)])
        self.update_worker(worker)

    def compilation_result(self, worker, champ_id, ret):
        hostname, port, slots, max_slots = worker
        w = self.workers[(hostname, port)]
        w.remove_compilation_task(champ_id)
        ioloop.add_callback(self.complete_compilation, champ_id, ret)

    def complete_compilation(self, champ_id, ret):
        if ret is True:
            status = 'ready'
        else:
            status = 'error'

        logging.info('compilation of champion %d: %s' % (champ_id, status))

        db = self.connect_to_db()
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            self.config['sql']['queries']['set_champion_status'],
            { 'champion_id': champ_id, 'champion_status': status }
        )
        db.commit()

    def match_ready(self, worker, match_id, req_port, sub_port):
        logging.debug('match %(match_id)d ready on %(worker)s port %(req_port)d %(sub_port)d'
                          % locals())

    def match_done(self, worker, mid, result):
        db = self.connect_to_db()
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        logging.info('match %(mid)d ended' % locals())

        to_update = [
            { 'player_id': r[0], 'player_score': r[1] }
            for r in result
        ]
        cur.executemany(
            self.config['sql']['queries']['set_player_score'],
            to_update
        )

        cur.execute(
            self.config['sql']['queries']['set_match_status'],
            { 'match_id': mid, 'match_status': 'done' }
        )

        to_update = [
            { 'match_id': mid, 'champion_score': r[1], 'player_id': r[0] }
            for r in result
        ]
        cur.executemany(
            self.config['sql']['queries']['update_tournament_score'],
            to_update
        )

        db.commit()
        self.workers[(worker[0], worker[1])].remove_match_task(mid)

    def client_done(self, worker, mpid):
        self.workers[(worker[0], worker[1])].remove_player_task(mpid)

    def redispatch_worker(self, worker):
        worker.kill_tasks()
        tasks = [t for (t, g) in worker.tasks]
        if tasks:
            logging.info("redispatching tasks for %s: %s" % (
                             worker, tasks
                        ))
            self.worker_tasks = tasks + self.worker_tasks
            ioloop.add_callback(dispatcher_task)
        del self.workers[(worker.hostname, worker.port)]

    @tornado.gen.coroutine
    def janitor_task(self):
        while True:
            all_workers = copy.copy(self.workers)
            for worker in all_workers.values():
                if not worker.is_alive(self.config['worker']['timeout_secs']):
                    logging.warn("timeout detected for worker %s" % worker)
                    self.redispatch_worker(worker)

            yield tornado.gen.Task(ioloop.add_timeout, time.time() + 1)

    def connect_to_db(self):
        return psycopg2.connect(
            host=self.config['sql']['host'],
            port=self.config['sql']['port'],
            user=self.config['sql']['user'],
            password=self.config['sql']['password'],
            database=self.config['sql']['database'],
        )

    def check_requested_compilations(self, status='new'):
        cur = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            self.config['sql']['queries']['get_champions'],
            { 'champion_status': status }
        )

        to_set_pending = []
        for r in cur:
            logging.info('requested compilation for %(name)s / %(id)d' % r)
            to_set_pending.append({
                'champion_id': r['id'],
                'champion_status': 'pending'
            })
            t = task.CompilationTask(self.config, r['name'], r['id'])
            self.worker_tasks.append(t)

        if to_set_pending:
            ioloop.add_callback(dispatcher_task)

        cur.executemany(
            self.config['sql']['queries']['set_champion_status'],
            to_set_pending
        )
        self.db.commit()

    def check_requested_matches(self, status='new'):
        cur = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            self.config['sql']['queries']['get_matches'],
            { 'match_status': status }
        )

        to_set_pending = []
        for r in cur:
            logging.info('request match id %(match_id)d launch' % r)
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
            ioloop.add_callback(dispatcher_task)

        cur.executemany(
            self.config['sql']['queries']['set_match_status'],
            to_set_pending
        )
        self.db.commit()

    @tornado.gen.coroutine
    def dbwatcher_task(self):
        self.db = self.connect_to_db()
        self.check_requested_compilations('pending')
        self.check_requested_matches('pending')
        while True:
            self.check_requested_compilations()
            self.check_requested_matches()
            yield tornado.gen.Task(ioloop.add_timeout, time.time() + 1)

    def find_worker_for(self, task):
        available = list(self.workers.values())
        available = [w for w in available if w.can_add_task(task)]
        random.shuffle(available)
        available.sort(key=lambda w: w.usage)
        if not available:
            return None
        else:
            return available[0]

    @tornado.gen.coroutine
    def dispatcher_task(self):
        if self.worker_tasks:
            task = self.worker_tasks[0]
            w = self.find_worker_for(task)
            if w is None:
                logging.info("no worker available for task %s" % task)
            else:
                w.add_task(self, task)
                logging.debug("task %s got to %s" % (task, w))
                self.worker_tasks = self.worker_tasks[1:]
        yield tornado.gen.Task(ioloop.add_timeout, time.time() + 0.1)
        if self.worker_tasks:
            ioloop.add_callback(dispatcher_task)

class MasterNodeProxy(prologin.rpc.server.BaseRPCApp):
    def __init__(self, *args, master=None **kwargs):
        super().__init__(*args, **kwargs)
        self.master = master

    @prologin.rpc.server.remote_method
    def heartbeat(self, worker, first):
        self.master.heartbeat(worker, first)
        return True

    @prologin.rpc.server.remote_method
    def compilation_result(self, worker, champ_id, ret):
        self.master.update_worker(worker)
        self.master.compilation_result(worker, champ_id, ret)
        return True

    @prologin.rpc.server.remote_method
    def match_ready(self, worker, match_id, req_port, sub_port):
        self.master.update_worker(worker)
        self.master.match_ready(worker, match_id, req_port, sub_port)
        return True

    @prologin.rpc.server.remote_method
    def match_done(self, worker, mid, result):
        self.master.update_worker(worker)
        self.master.match_done(worker, mid, result)
        return True

    @prologin.rpc.server.remote_method
    def client_ready(self, worker, mid, mpid):
        self.master.update_worker(worker)
        return True

    @prologin.rpc.server.remote_method
    def client_done(self, worker, mid, mpid, retcode):
        self.master.update_worker(worker)
        self.master.client_done(worker, mpid)
        return True

    @prologin.rpc.server.remote_method
    def status(self):
        return self.master.status

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-l', '--local-logging', action='store_true',
                      dest='local_logging', default=False,
                      help='Activate logging to stdout.')
    parser.add_option('-v', '--verbose', action='store_true',
                      dest='verbose', default=False,
                      help='Verbose mode.')
    options, args = parser.parse_args()

    prologin.log.setup_logging('master-node', verbose=options.verbose,
                               local=options.local_logging)

    config = prologin.config.load('master-node')

    master = MasterNode(config)
    s = MasterNodeProxy(app_name='master-node', master=master,
        secret=config['master']['shared_secret'].encode('utf-8'))
    s.listen(config['master']['port'])

    try:
        ioloop.instance().start()
    except KeyboardInterrupt:
        pass
