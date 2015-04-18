#!/usr/bin/env python

import logging
import sys
import prologin.config
import prologin.log
import prologin.mdb.client
import prologin.web
import prologin.presencesync.client
import prologin.udb.client
import threading
import tornado.web
import tornado.ioloop


class WhoisHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        try:
            ipaddr = self.get_query_argument("ip")
        except tornado.web.MissingArgumentError:
            self.send_error(400)
            return
        with self.application.lock:
            login = self.application.ip_to_login.get(ipaddr, "")
        if not login:
            logging.warning("%s requested /whois for unknown IP %s",
                            self.request.remote_ip, ipaddr)
        self.write(login + "\n")
        self.finish()


class PresenceCacheServer(prologin.web.TornadoApp):
    def __init__(self, port, app_name):
        super().__init__(self.get_handlers(), app_name)
        self.ip_to_login = {}
        self.port = port
        self.lock = threading.Lock()

    def get_handlers(self):
        """Return a list of URL/request handlers couples for this server."""
        return [
            (r'/whois', WhoisHandler),
        ]

    def start(self):
        """Run the server."""
        # NOTE: this threading stuff has seirl seal-of-approval: "It's fine
        # because it's not related to the server."
        # poll_updates() is rather intricate, it would be overkill
        # to reimplement here.
        def presencesync_daemon():
            return prologin.presencesync.client.connect().poll_updates(
                self.presencesync_callback)
        thread = threading.Thread(target=presencesync_daemon)
        thread.deamon = True  # exit along with main
        self.listen(self.port)
        thread.start()
        tornado.ioloop.IOLoop.instance().start()

    def presencesync_callback(self, login_to_machine, updates_metadata):
        mdb_machines = prologin.mdb.client.connect().query()  # get all machines

        # Translate hostnames to IPs
        ip_to_hostname = {m['ip']: m['hostname'] for m in mdb_machines}
        # Translates logins to hostnames
        hostname_to_login = {m['hostname']: login for login, m in login_to_machine.items()}

        with self.lock:
            # FIXME: self.ip_to_login may contain multiple similar logins
            # eg. {1.2.3.4: fubar, 4.3.2.1: fubar}
            # May not be a big deal though. We could clear the mapping before
            # building it.
            for ip, hostname in ip_to_hostname.items():
                try:
                    self.ip_to_login[ip] = hostname_to_login[hostname]
                except KeyError:
                    # Clear login for this IP as its hostname was not found
                    # (eg. because the machine became free)
                    self.ip_to_login.pop(ip, None)

            length = len(self.ip_to_login)

        logging.info("Received %d logins, %d hostnames. Cache has %d mappings.",
                     len(login_to_machine), len(mdb_machines), length)


if __name__ == '__main__':
    prologin.log.setup_logging('presencesync_cacheserver')
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    server = PresenceCacheServer(port, 'cacheserver')
    server.start()
