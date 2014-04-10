# -*- encoding: utf-8 -*-
# This file is part of Prologin-SADM.
#
# Copyright (c) 2013-2014 Antoine Pietri <antoine.pietri@prologin.org>
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
import os.path
import optparse
import prologin.log
import prologin.config
import prologin.rpc.client
import prologin.rpc.server
import re
import socket
import time
import tornado
import tornado.platform.asyncio
import yaml

from . import operations

ioloop = asyncio.get_event_loop()
tornado.platform.asyncio.AsyncIOMainLoop().install()


def async_work(func=None, slots=0):
    if func is None:
        return functools.partial(async_work, slots=slots, callback=callback)
    @functools.wrap(func)
    def mktask(self, *args, **kwargs):
        @asyncio.coroutine
        def wrapper(self, *wargs, **wkwargs):
            if self.slots < slots:
                logging.warn('not enough slots to start the required job')
            logging.debug('starting a job for %d slots' % slots)
            self.slots -= slots
            yield from self.update_master()
            try:
                r = yield from func(self, *wargs, **wkwargs)
            finally:
                self.slots += slots
                yield from self.update_master()
        asyncio.Task(wrapper(self, *args, **kwargs))
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
        self.min_srv_port = config['worker']['port_range_start']
        self.max_srv_port = config['worker']['port_range_end']
        self.srv_port = self.min_srv_port
        self.matches = {}
        asyncio.Task(self.send_heartbeat)
        self.master = self.get_master()

    def get_worker_infos(self):
        return (self.hostname, self.port, self.slots, self.max_slots)

    def get_master(self):
        config = self.config
        host, port = (config['master']['host'], config['master']['port'])
        url = "http://{}:{}/".format(host, port)
        return prologin.rpc.client.Client(url,
                secret=config['master']['shared_secret'].encode('utf-8'))

    @asyncio.coroutine
    def update_master(self):
        yield from loop.run_in_executor(self.master.update, get_worker_infos())

    @asyncio.coroutine
    def send_heartbeat(self):
        logging.info('sending heartbeat to the server, %d/%d slots' % (
            self.slots, self.max_slots
        ))
        first_heartbeat = True
        while True:
            try:
                self.master.heartbeat(self.get_worker_infos(), first_heartbeat)
                first_heartbeat = False
            except socket.error:
                msg = 'master down, retrying heartbeat in %ds' % self.interval
                logging.warn(msg)

            yield from asyncio.sleep(self.interval)

    @prologin.rpc.server.remote_method
    def available_server_port(self):
        """
        Be optimistic and hope that:
        - nobody will use the ports in the port range but us
        - there will never be more servers than ports in the range
        """
        port = self.srv_port
        self.srv_port += 1
        if self.srv_port > self.max_srv_port:
            self.srv_port = self.min_srv_port
        return port

    @async_work(slots=1)
    @prologin.rpc.server.remote_method
    def compile_champion(self, cid, champion_tgz):
        cpath = os.path.join(self.config['path']['champion'], str(cid))
        compiled_path = os.path.join(cpath, 'champion-compiled.tar.gz')
        log_path = os.path.join(cpath, 'compilation.log')

        yield from loop.run_in_executor(operations.untar, champion_tgz, cpath)
        ret = yield from operations.compile_champion(self.config, cpath)

        if not ret:
            compilation_content = b''
        else:
            with open(compiled_path, 'rb') as f:
                compilation_content = f.read()
        with open(log_path, 'r') as f:
            log_content = f.read()

        yield from loop.run_in_executor(self.master.compilation_result, cid,
                compilation_content, log_content)

    @async_work(slots=1)
    @prologin.rpc.server.remote_method
    def run_server(self, rep_port, pub_port, contest, match_id, opts=''):
        logging.info('starting server for match {}'.format(match_id))
        yield from operations.run_server(self.config, worker.server_done,
                                         rep_port, pub_port, contest, match_id,
                                         opts)
        logging.info('match {} done'.format(match_id))

        lines = stdout.split('\n')
        result = []
        score_re = re.compile(r'^(\d+) (-?\d+) (-?\d+)$')
        for line in lines:
            m = score_re.match(line)
            if m is None:
                continue
            pid, score, stat = m.groups()
            result.append((int(pid), int(score)))

        try:
            self.master.match_done(self.get_worker_infos(), match_id, result)
        except socket.error:
            pass

    @async_work(slots=2)
    @prologin.rpc.server.remote_method
    def run_client(self, match_id, ip, req_port, sub_port, user, pl_id, opts):
        logging.info('running champion %d from %s for match %d' % (
                         champ_id, user, match_id
        ))
        operations.run_client(self.config, ip, req_port, sub_port, contest, match_id, user,
                              champ_id, pl_id, opts, self.client_done)
        logging.info('champion %d for match %d done' % (champ_id, match_id))
        try:
            self.master.client_done(self.get_worker_infos(),
                                    match_id, pl_id, retcode)
        except socket.error:
            pass


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-l', '--local-logging', action='store_true',
                      dest='local_logging', default=False,
                      help='Activate logging to stdout.')
    parser.add_option('-v', '--verbose', action='store_true',
                      dest='verbose', default=False,
                      help='Verbose mode.')
    options, args = parser.parse_args()

    prologin.log.setup_logging('worker-node', verbose=options.verbose,
                               local=options.local_logging)

    config = prologin.config.load('worker-node')

    s = WorkerNode(app_name='worker-node', config=config,
            secret=config['master']['shared_secret'].encode('utf-8'))
    s.listen(config['worker']['port'])

    try:
        ioloop.run_forever()
    except KeyboardInterrupt:
        pass
