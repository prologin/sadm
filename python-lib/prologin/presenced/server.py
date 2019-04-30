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
import prologin.config
import prologin.log
import prologin.presenced.client
import prologin.presencesync.client
import prologin.synchronisation
import prologin.tornadauth
import prologin.web
import socket
import subprocess
import sys
import threading
import time
import tornado.ioloop
import tornado.web


CLT_CFG = prologin.config.load('presenced-client')

HOSTNAME = '.'.join(socket.gethostname().split('.')[:-1])  # Remove .prolo

if 'shared_secret' not in CLT_CFG:
    raise RuntimeError(
        'Missing shared_secret in the presenced-client YAML config'
    )


def get_logged_prologin_users():
    """Return the list of logged user that are handled by Prologin."""
    result = set()
    # FIXME: we used to use who(1) but sddm does not use utmp to log
    # session opening, hence the hack with ps
    users = set(subprocess.check_output(['ps', '-axho', '%U']).split(b'\n'))
    for line in users:
        if not line.strip():
            continue
        login = line.decode('ascii')
        try:
            if prologin.presenced.client.is_prologin_user(login):
                result.add(login)
        except KeyError:
            pass
    return result


class SendHeartbeatHandler(tornado.web.RequestHandler):
    @prologin.tornadauth.signature_checked('secret', check_msg=True)
    def post(self, msg):
        logins = get_logged_prologin_users()
        logging.debug("Heartbeat: logged-in users: %s", logins)
        if len(logins) == 0:
            self.set_status(200, 'OK, no one logged in')
        elif len(logins) == 1:
            self.application.presencesync.send_heartbeat(
                logins.pop(), HOSTNAME
            )
            self.set_status(200, 'OK, one user logged in')
        else:
            logging.error('There are too many users logged in: %s',
                          ', '.join(logins))
            self.set_status(500, 'Too many users logged in')


class LoginHandler(tornado.web.RequestHandler):
    @prologin.tornadauth.signature_checked('secret', check_msg=True)
    def post(self, msg):
        login = json.loads(msg)['login']
        result = self.application.presencesync.request_login(
            login, HOSTNAME
        )
        if result is not None:
            self.set_status(423, 'Login refused')
            self.write(result)
        else:
            self.set_status(200, 'OK')


class PresencedServer(prologin.web.TornadoApp):
    def __init__(self, secret, port):
        super(PresencedServer, self).__init__([
            (r'/send_heartbeat', SendHeartbeatHandler),
            (r'/login', LoginHandler),
        ], 'presenced')
        self.presencesync = prologin.presencesync.client.connect(publish=True)
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
        conn = prologin.presenced.client.connect()
        delay = prologin.presencesync.client.SUB_CFG['timeout'] / 2
        while True:
            # Communicate with the Presenced server just like any other client
            # in order to handle concurrent accesses nicely.

            # Try to send a message, forever and ever and ever.
            try:
                conn.send_heartbeat()
            except Exception:
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
