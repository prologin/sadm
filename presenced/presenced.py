# -*- encoding: utf-8 -*-
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

"""Presenced server: periodically send a heartbeat to the PresencSync server
and transmits login requests from pam_presenced.
"""

import json
import logging
import os
import prologin.config
import prologin.log
import prologin.presenced
import prologin.presencesync
import prologin.synchronisation
import socket
import subprocess
import sys
import threading
import time
import tornado.ioloop
import tornado.web


CLT_CFG = prologin.config.load('presenced-client')

HOSTNAME = socket.gethostname().split('.')[:-1]  # Remove .prolo

if 'shared_secret' not in CLT_CFG:
    raise RuntimeError(
        'Missing shared_secret in the presenced-client YAML config'
    )


def get_logged_prologin_users():
    """Return the list of logged user that are handled by Prologin."""
    result = set()

    with open(os.devnull, 'r') as devnull:
        who = subprocess.Popen(
            ['who'], stdin=devnull, stdout=subprocess.PIPE
        )
        out, err = who.communicate()
    for line in out.split(b'\n'):
        if not line.strip():
            continue
        login = line.split()[0].decode('ascii')
        if prologin.presenced.is_prologin_user(login):
            result.add(login)

    return result


class SendHeartbeatHandler(tornado.web.RequestHandler):
    @prologin.tornadauth.signature_checked('secret', check_msg=True)
    def post(self, msg):
        logins = get_logged_prologin_users()
        if len(logins) == 0:
            self.set_status(200, 'OK, no one logged in')
        elif len(logins) == 1:
            self.application.presencesync.send_heartbeat(
                logins.pop(), HOSTNAME
            )
            self.set_status(200, 'OK, one user logged in')
        else:
            logging.error('There are too many users logged in: {}'.format(
                ', '.join(logins)
            ))
            self.set_status(500, 'Too many users logged in')

class LoginHandler(tornado.web.RequestHandler):
    @prologin.tornadauth.signature_checked('secret', check_msg=True)
    def post(self, msg):
        login = json.loads(msg)['login']
        result = self.application.presencesync.request_login(
            login, HOSTNAME
        )
        if result:
            self.set_status(423, 'Login refused')
            self.write(result)
        else:
            self.set_status(200, 'OK')


class PresencedServer(tornado.web.Application):
    def __init__(self, secret, port):
        super(PresencedServer, self).__init__([
            (r'/send_heartbeat', SendHeartbeatHandler),
            (r'/login', LoginHandler),
        ])
        self.presencesync = prologin.presencesync.connect(pub=True)
        self.secret = secret.encode('ascii')
        self.port = port

    def start(self):
        """Run the server."""
        self.listen(self.port)
        self.heartbeat_thread = threading.Thread(
            target=self.heartbeat_loop,
            daemon=True
        )
        self.heartbeat_thread.start()
        tornado.ioloop.IOLoop.instance().start()

    def heartbeat_loop(self):
        """Loop forever, asking the Precenced server to send a heartbeat
        periodically.
        """
        conn = prologin.presenced.connect()
        delay = prologin.presencesync.SUB_CFG['timeout'] / 2
        while True:
            # Communicate with the Presenced server just like any other client
            # in order to handle concurrent accesses nicely.

            # Try to send a message, forever and ever and ever.
            try:
                conn.send_heartbeat()
            except Exception as e:
                logging.exception(
                    'Heartbeat thread: error while sending a message to'
                    ' the Presenced server, retrying in 2s'
                )
                time.sleep(2)
            else:
                time.sleep(delay)


if __name__ == '__main__':
    prologin.log.setup_logging('presenced')
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    server = PresencedServer(CLT_CFG['shared_secret'], port)
    server.start()
