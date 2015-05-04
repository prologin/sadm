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

We don't use Tornado for this service because it *sucks* at large file
handling. tornado.iostream seems to buffer data when one side of the stream is
too slow (read or write) instead of trying to throttle. When transfering 5GB
files, buffering in RAM is just not a good idea.
"""

# TODO(delroth): authentify all the request handlers with HMAC

import gzip
import time
import http.server
import json
import logging
import os
import os.path
import postgresql
import prologin.config
import prologin.log
import prologin.mdb.client
import random
import signal
import socket
import struct
import subprocess
import sys
import urllib.parse
import urllib.request

from .monitoring import (
    hfs_get_hfs,
    hfs_migrate_remote_user,
    hfs_migrate_user,
    hfs_new_user,
    hfs_running_nbd,
    monitoring_start)
from socketserver import ThreadingMixIn

CFG = prologin.config.load('hfs-server')
CLT_CFG = prologin.config.load('hfs-client')

if 'shared_secret' not in CLT_CFG:
    raise RuntimeError('Missing shared_secret in the hfs-client YAML config')

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


def get_hfs_ip(hfs_id):
    """Returns the IPv4 address associated to an HFS. Assumes the HFS will have
    an alias "hfs%d" on it.
    """
    hfs_alias = 'hfs%d' % hfs_id
    potential_hfs = prologin.mdb.client.connect().query(
            aliases__contains=hfs_alias)

    # We need to loop over the results to avoid hfs1 matching hfs10.
    for server in potential_hfs:
        aliases = server['aliases'].split(',')
        if hfs_alias in aliases:
            return server['ip']

    raise ValueError("Unable to find HFS %d in MDB" % hfs_id)


def get_available_space(path):
    """Returns the number of bytes available on the FS containing <path>."""
    s = os.statvfs(os.path.dirname(path))
    return s.f_bsize * s.f_bavail


class ArgumentMissing(Exception):
    pass


class HFSRequestHandler(http.server.BaseHTTPRequestHandler):
    def get_argument(self, name):
        """Returns the value of the GET argument called <name>. If it does not
        exist, send an error page."""
        qs = self.post_data.decode('utf-8')
        args = urllib.parse.parse_qs(qs)
        data = json.loads(args['data'][0])
        if name not in data:
            raise ArgumentMissing(name)
        return data[name]

    def do_POST(self):
        rfile_len = int(self.headers['content-length'])
        self.post_data = self.rfile.read(rfile_len)
        try:
            if self.path.startswith('/get_hfs'):
                self.get_hfs()
            elif self.path.startswith('/migrate_user'):
                self.migrate_user()
            else:
                self.send_error(404)
        except ArgumentMissing as e:
            self.send_error(400, message=str(e))
        except Exception as e:
            self.send_error(501, message=str(e))
            logging.exception('Something wrong happened')

    def migrate_user(self):
        migrate_user_start = time.monotonic()

        # If we have a nbd-server for that user, kill it.
        self.user = self.get_argument('user')
        self.hfs = int(self.get_argument('hfs'))
        self.kill_user_nbd()

        self.send_response(200)
        self.end_headers()
        with gzip.GzipFile(mode='wb', fileobj=self.wfile) as zfp:
            with open(self.nbd_filename(), 'rb') as fp:
                while True:
                    block = fp.read(65536)
                    if not block:
                        break
                    zfp.write(block)

        fname = self.nbd_filename()
        backup_fname = os.path.join(os.path.dirname(fname),
                                    'backup_' + os.path.basename(fname))
        os.rename(fname, backup_fname)

        labels = {'user': self.user, 'hfs': self.hfs}
        delta = time.monotonic() - migrate_user_start
        hfs_migrate_user.labels(labels).observe(delta)

    def get_hfs(self):
        get_hfs_start = time.monotonic()

        db = postgresql.open(CFG['db'])

        self.user = self.get_argument('user')
        self.user_type = self.get_argument('utype')

        # We can host several hfs on a single machine. We trust the client to
        # give us our hfs id when connecting to us. The alternative is looking
        # at the IP the client connected to.
        self.hfs = int(self.get_argument('hfs'))

        # TODO(delroth): potentially blocking, but fast
        get_user_hfs = db.prepare('SELECT hfs FROM user_location WHERE username = $1')
        location = get_user_hfs(self.user)

        if location == []:  # first case: home nbd does not exist yet
            self.new_user_handler()
            add_user_hfs = db.prepare('INSERT INTO user_location(username, hfs) VALUES ($1, $2)')
            add_user_hfs(self.user, self.hfs)
        else:
            location = location[0][0]
            if location != self.hfs:
                self.remote_user_handler(location)
                set_user_hfs = db.prepare('UPDATE user_location SET hfs = $2 WHERE username = $1')
                set_user_hfs(self.user, self.hfs)

        filename = self.nbd_filename()
        if not os.path.exists(filename):
            raise RuntimeError("NBD file to server for %s missing" % self.user)

        self.kill_user_nbd()

        port = self.start_nbd_server(filename)
        self.send_response(200)
        self.send_header('content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({ 'port': port }).encode('utf-8'))

        delta = time.monotonic() - get_hfs_start
        labels = {'user': self.user, 'user_type': self.user_type,
                  'hfs': self.hfs}
        hfs_get_hfs.labels(labels).observe(delta)

    def nbd_filename(self):
        """Returns the filename for the NBD."""
        dir_path = os.path.join(CFG['export_base'], 'hfs%d' % self.hfs)
        if not os.path.exists(dir_path):
            os.mkdir(dir_path, 0o700)
        return os.path.join(dir_path, '%s.nbd' % self.user)

    def kill_user_nbd(self):
        if self.user in RUNNING_NBD:
            # To make sure we don't have two machines writing on the same NBD
            # (would be very, very troublesome).
            try:
                os.kill(RUNNING_NBD[self.user]['pid'], signal.SIGKILL)
            except Exception:
                pass
            del RUNNING_NBD[self.user]
            hfs_running_nbd.dec()

    def get_nbd_size(self):
        """Returns the NBD size for the current user type."""
        if self.user_type == 'user':
            quota = 2 * 1024 * 1024 * 1024
        else:
            quota = 5 * 1024 * 1024 * 1024
        return quota

    def get_user_group(self):
        """Returns the UNIX group for the current user type."""
        if self.user_type == 'user':
            group = 'user'
        else:
            group = 'orga'
        return group

    def check_available_space(self):
        """Check if we have enough space to create or download a NBD for that
        user."""
        if get_available_space(self.nbd_filename()) < self.get_nbd_size():
            raise RuntimeError('out of disk space')

    def start_nbd_server(self, filename):
        """Starts the NBD server for a given filename. Allocates a random port
        between CFG['start_port_range'] and CFG['end_port_range'] (excl).
        Returns that port.
        """
        port = find_free_port(CFG['start_port_range'], CFG['end_port_range'])

        # Write config file, required as of nbd 3.10
        config_file = '/etc/nbd-server/%s' % self.user
        with open(config_file, 'w') as f:
            f.write("[generic]\n")
            f.write("port = %d\n" % port)
            f.write("[%s]\n" % self.user)
            f.write("exportname = %s\n" % filename)

        cmd = ['nbd-server',
            '-p', '/tmp/nbd.%s.pid' % self.user,
            '-C', config_file]
        proc = subprocess.Popen(cmd)
        if proc.wait() != 0:
            raise RuntimeError('Unable to start the nbd server')
        time.sleep(1)
        with open('/tmp/nbd.%s.pid' % self.user) as fp:
            pid = int(fp.read().strip())
            RUNNING_NBD[self.user] = { 'pid': pid, 'port': port }
            hfs_running_nbd.inc()
        return port

    def new_user_handler(self):
        """Handles creation of a new NBD file for the given user."""
        new_user_start = time.monotonic()

        code_dir = os.path.abspath(os.path.dirname(__file__))
        creation_script = os.path.join(code_dir, 'create_nbd.sh')

        self.check_available_space()

        quota = self.get_nbd_size()
        group = self.get_user_group()

        if os.path.exists(self.nbd_filename()):
            raise RuntimeError('nbd file for new user already exists')

        # Create a sparse file of the wanted size
        with open(self.nbd_filename(), 'wb') as f:
            f.truncate(quota)

        # Format the file and copy the skeleton
        cmd = [creation_script, self.nbd_filename(), self.user, group,
               CFG['skeleton'], self.user_type]

        self.proc = subprocess.Popen(cmd)
        error_code = self.proc.wait()
        if error_code != 0:
            raise RuntimeError('creation script failed!')

        delta = time.monotonic() - new_user_start
        labels = {'user': self.user, 'user_type': self.user_type}
        hfs_new_user.labels(labels).observe(delta)

    def remote_user_handler(self, peer_id):
        """Transfers the data from a remote HFS to the current HFS."""
        remote_user_start = time.monotonic()

        self.check_available_space()

        url = ('http', 'hfs%d:%d' % (peer_id, CFG['port']), '/migrate_user',
               '', '')
        url = urllib.parse.urlunsplit(url)
        data = { 'user': self.user, 'hfs': peer_id }
        data = 'data=%s' % (urllib.parse.quote(json.dumps(data)))
        data = data.encode('utf-8')

        with open(self.nbd_filename(), 'wb') as fp:
            with urllib.request.urlopen(url, data=data) as rfp:
                with gzip.GzipFile(fileobj=rfp, mode='rb') as zfp:
                    while True:
                        block = zfp.read(65536)
                        if not block:
                            break
                        fp.write(block)

        delta = time.monotonic() - remote_user_start
        labels = {'user': self.user, 'hfs': peer_id}
        hfs_migrate_remote_user.labels(labels).observe(delta)

class ThHTTPServer(http.server.HTTPServer, ThreadingMixIn):
    pass

if __name__ == '__main__':
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print('usage: %s <hfs-number>' % sys.argv[0])
        sys.exit(1)

    hfs_id = int(sys.argv[1])
    prologin.log.setup_logging('hfs-%d' % hfs_id)
    hfs_ip = get_hfs_ip(hfs_id)
    server = ThHTTPServer((hfs_ip, CFG['port']), HFSRequestHandler)

    monitoring_start(hfs_ip)

    server.serve_forever()
