#!/usr/bin/env python

import asyncio
import logging
import sys

from aiohttp import web

import prologin.config
import prologin.log
import prologin.mdbsync.client
import prologin.presencesync.client
from prologin.synchronisation import AsyncClient


class PresenceSyncSSOServer:
    """
    A web server that implements nginx auth_request_ protocol to authenticate users through udb/mdb.

    nginx auth_request_ protocol is simple:

    * on successful authentication, reply with HTTP/2xx
    * on unsuccessful authentication, reply with HTTP/401 or HTTP/403

    Here we find the user logged on host X-Real-IP (through udb/mdb) and set:

    * a header containing the corresponding user login (if found) for use in the
      authentication backend (eg. Django's RemoteUserMiddleware_ with ``HEADER = 'X-SSO-User'``)
    * a header containing the status of the check, for debugging purposes

    In all cases, we always return a valid (2xx) reply because we just want to set some headers, not
    actually return 4xx responses to users. In the event of a missing ``X-SSO-User``, the web app
    (typically Django) can then fallback to another authentication method (typically a login form
    against the local user database).

    .. _auth_request: http://nginx.org/en/docs/http/ngx_http_auth_request_module.html
    .. _RemoteUserMiddleware: https://docs.djangoproject.com/en/stable/howto/auth-remote-user/#configuration
    """

    HEADER_REAL_IP = "X-Real-IP"
    HEADER_SSO_USER = "X-SSO-User"
    HEADER_SSO_STATUS = "X-SSO-Status"

    def __init__(self):
        # Kept up-to-date through polling in another thread.
        self.mdb_machines = {}
        # Kept up-to-date through polling in another thread.
        self.login_to_machine = {}
        # Computed in update_cache().
        self.ip_to_hostname = {}
        self.hostname_to_login = {}

    def make_app(self):
        app = web.Application()
        app.add_routes([web.get('/', self.handle_auth_request)])
        return app

    async def handle_auth_request(self, request):
        # Find the remote making the request. This is for debugging purposes
        # only, not for authenticating.
        remote_headers = (request.headers.get(h) for h in
                          ("X-Real-Host", "X-Forwarded-For", "X-Real-IP"))
        remote = next(filter(bool, remote_headers), "unknown")

        def response(status, login=None):
            headers = {self.HEADER_SSO_STATUS: status}
            if login:
                headers[self.HEADER_SSO_USER] = login
            return web.Response(status=204, headers=headers)

        try:
            ipaddr = request.headers[self.HEADER_REAL_IP]
        except KeyError:
            logging.warning(
                "%s sent a malformed SSO auth request (no %s header)",
                remote, self.HEADER_REAL_IP)
            return response(f"missing header {self.HEADER_REAL_IP}")

        try:
            hostname = self.ip_to_hostname[ipaddr]
        except KeyError:
            logging.warning("%s requested SSO login for unknown IP %s",
                            remote, ipaddr)
            return response(f"unknown IP {ipaddr}")

        try:
            login = self.hostname_to_login[hostname]
        except KeyError:
            logging.warning("%s requested SSO login for logged-out hostname %s "
                            "(%s)", remote, hostname, ipaddr)
            return response(f"logged-out machine {hostname}")

        logging.debug("%s requested SSO login for %s → %s → '%s'",
                      remote, ipaddr, hostname, login)
        return response("authenticated", login)

    def update_cache(self):
        self.ip_to_hostname = {m['ip']: m['hostname']
                               for m in self.mdb_machines.values()}

        self.hostname_to_login = {
            m['hostname']: login
            for login, m in self.login_to_machine.items()}

        logging.debug("Cache updated: %d IP-to-hostname mappings, %d "
                      "hostname-to-login mappings",
                      len(self.ip_to_hostname), len(self.hostname_to_login))


if __name__ == '__main__':
    prologin.log.setup_logging('presencesync_sso')

    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000


    async def serve():
        server = PresenceSyncSSOServer()

        web_runner = web.AppRunner(server.make_app())
        await web_runner.setup()
        web_server = web.TCPSite(web_runner, '127.0.0.1', port)
        await web_server.start()

        mdbsync_client = prologin.mdbsync.client.aio_connect()
        presencesync_client = prologin.presencesync.client.aio_connect()

        def sync_dict(client: AsyncClient, dict_to_update):
            async def coroutine():
                async for state, meta in client.poll_updates():
                    dict_to_update.clear()
                    dict_to_update.update(state)
                    server.update_cache()

            return asyncio.create_task(coroutine())

        tasks = [
            sync_dict(mdbsync_client, server.mdb_machines),
            sync_dict(presencesync_client, server.login_to_machine),
        ]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        [task.cancel() for task in tasks]
        await web_runner.cleanup()


    asyncio.run(serve())
