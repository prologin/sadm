# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2013 Association Prologin <info@prologin.org>
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

"""Home Filesystem Server: handle creation and migration of filesystems for
/home/<user>.

Each user home directory is a separate filesystem served using NBD (Network
Block Device). When a user logs in to a machine, the PAM session_start script
is executed and will ask the HFS responsible for the machine for the port to
connect to for NBD. Three things can happen on the HFS side:

  * The user has currently no home directory: we create a new one, copy the
    skeleton in it, serve it and return the port.
  * The user has a home directory and it is on this server: serve it and return
    the port.
  * The user has a home directory on another server. We ask the remote HFS for
    the data, then serve it and return the port.

The user<->hfs association is stored in a shared database hosted on ``db``
(PostgreSQL).
"""

# TODO(delroth): authentify all the request handlers with HMAC

import logging
import os
import os.path
import postgresql
import prologin.config
import prologin.log
import prologin.mdb
import random
import signal
import socket
import tornado.ioloop
import tornado.gen
import tornado.process
import tornado.web


CFG = prologin.config.load('hfs-server')

if 'shared_secret' not in CFG:
    raise RuntimeError('Missing shared_secret in the hfs-server YAML config')

DB = postgresql.open(CFG['db'])

get_user_hfs = DB.prepare('SELECT hfs FROM user_location WHERE username = $1')
set_user_hfs = DB.prepare('UPDATE user_location SET hfs = $2 WHERE username = $1')
add_user_hfs = DB.prepare('INSERT INTO user_location(username, hfs) VALUES ($1, $2)')

# { 'user1': { 'pid': 4242, 'port': 1234 }, ... }
RUNNING_NBD = {}

def find_free_port(start, end):
    """Finds a free port in [start, end[."""
    s = socket.socket()
    while True:
        port = random.randrange(start, end)
        try:
            s.bind(('0.0.0.0', port))
            s.close()
            return port
        except socket.error:
            continue


def get_available_space(path):
    """Returns the number of bytes available on the FS containing <path>."""
    s = os.statvfs(os.path.dirname(path))
    return s.f_bsize * s.f_bavail


class GetHFSHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        self.user = self.get_argument('user')
        self.user_type = self.get_argument('utype')

        # We can host several hfs on a single machine. We trust the client to
        # give us our hfs id when connecting to us. The alternative is looking
        # at the IP the client connected to.
        self.hfs = int(self.get_argument('hfs'))

        # TODO(delroth): potentially blocking, but fast
        location = get_user_hfs(self.user)

        if location == []:  # first case: home nbd does not exist yet
            yield from self.new_user_handler()
            add_user_hfs(self.user, self.hfs)
        else:
            location = location[0][0]
            if location != hfs:
                yield from self.remote_user_handler()
                set_user_hfs(self.user, self.hfs)

        filename = self.nbd_filename()
        if not os.path.exists(filename):
            raise RuntimeError("NBD file to server for %s missing" % self.user)

        if self.user in RUNNING_NBD:
            # To make sure we don't have two machines writing on the same NBD
            # (would be very, very troublesome).
            os.kill(RUNNING_NBD[self.user]['pid'], signal.SIGKILL)

        port = self.start_nbd_server(filename)
        self.write({ 'port': port })
        self.finish()

    def nbd_filename(self):
        """Returns the filename for the NBD."""
        dir_path = os.path.join(CFG['export_base'], 'hfs%d' % self.hfs)
        if not os.path.exists(dir_path):
            os.mkdir(dir_path, 0o700)
        return os.path.join(dir_path, '%s.nbd' % self.user)

    def start_nbd_server(self, filename):
        """Starts the NBD server for a given filename. Allocates a random port
        between CFG['start_port_range'] and CFG['end_port_range'] (excl).
        Returns that port.
        """
        port = find_free_port(CFG['start_port_range'], CFG['end_port_range'])
        command = 'nbd-server -p /tmp/nbd.%(user)s.pid %(port)d %(filename)s'
        if os.system(command % { 'user': self.user, 'port': port,
                                 'filename': filename }) != 0:
            raise RuntimeError('Unable to start the nbd server')
        with open('/tmp/nbd.%s.pid' % self.user) as fp:
            pid = int(fp.read().strip())
            RUNNING_NBD[self.user] = { 'pid': pid, 'port': port }
        return port

    def new_user_handler(self):
        """Handles creation of a new NBD file for the given user."""
        code_dir = os.path.abspath(os.path.dirname(__file__))
        creation_script = os.path.join(code_dir, 'create_nbd.sh')
        if self.user_type == 'user':
            quota = 2 * 1024 * 1024 * 1024
            group = 'user'
        else:
            quota = 5 * 1024 * 1024 * 1024
            group = 'orga'

        if get_available_space(self.nbd_filename()) < quota:
            raise RuntimeError('out of disk space')

        if os.path.exists(self.nbd_filename()):
            raise RuntimeError('nbd file for new user already exists')

        # Create a sparse file of the wanted size
        with open(self.nbd_filename(), 'w') as f:
            f.truncate(quota)

        # Format the file and copy the skeleton
        cmd = [creation_script, self.nbd_filename(), self.user,
               CFG['skeleton']]
        self.proc = tornado.process.Subprocess(cmd,
                io_loop=tornado.ioloop.IOLoop.instance())
        self.proc.set_exit_callback((yield tornado.gen.Callback('cmd')))
        error_code = yield tornado.gen.Wait('cmd')
        if error_code != 0:
            raise RuntimeError('creation script failed!')

    def remote_user_handler(


class MigrateUserHandler(tornado.web.RequestHandler):
    def get(self):
        return 'Not yet implemented'


application = tornado.web.Application([
    # PAM <-> HFS
    (r'/get_hfs', GetHFSHandler),

    # HFS <-> HFS
    (r'/migrate_user', MigrateUserHandler),
])


if __name__ == '__main__':
    prologin.log.setup_logging('hfs')
    application.listen(CFG['port'])
    tornado.ioloop.IOLoop.instance().start()
