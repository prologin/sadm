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

"""Netboot HTTP server, getting data from MDB and serving iPXE config chunks.

This is required mostly because 1. we don't want mdb to have iPXE related
things (shouldn't bring specifics into a generic server); 2. iPXE scripting is
not expressive enough to be able to query MDB and then store the results in a
variable.
"""

import os
import prologin.config
import prologin.log
import prologin.mdb.client
import requests
import tornado.ioloop
import tornado.web
import tornado.wsgi


CFG = prologin.config.load('netboot')

BOOT_UNKNOWN_SCRIPT = """#!ipxe
echo An error occurred: netboot can't find the MAC in MDB.
echo Sleeping for 30s and rebooting.
sleep 30
reboot
"""

BOOT_SCRIPT = """#!ipxe
echo Booting the kernel on %(rfs_ip)s:/nfsroot
initrd http://netboot/static/initrd%(suffix)s
boot http://netboot/static/kernel%(suffix)s nfsroot=%(rfs_ip)s:/export/nfsroot,ro %(options)s
"""

REGISTER_ERROR_SCRIPT = """#!ipxe
echo Registration failure! Something went wrong: %(err)s
echo Waiting for 30s and rebooting.
sleep 30
reboot
"""

REGISTER_DONE_SCRIPT = """#!ipxe
echo Registration done! Waiting for 30s and rebooting.
sleep 30
reboot
"""

class BootHandler(tornado.web.RequestHandler):
    def get(self, mac):
        self.content_type = 'text/plain; charset=utf-8'
        # TODO(delroth): This is blocking - not perfect... should be fast
        # though.
        machine = prologin.mdb.client.connect().query(mac=mac)
        if len(machine) != 1:
            self.finish(BOOT_UNKNOWN_SCRIPT)

        machine = machine[0]
        rfs_hostname = 'rfs%d' % machine['rfs']
        rfs = prologin.mdb.client.connect().query(aliases__contains=rfs_hostname)
        try:
            rfs_ip = rfs[0]['ip']
        except IndexError:
            script = REGISTER_ERROR_SCRIPT % {
                    'err': 'No such RFS: %s' % rfs_hostname }
            self.finish(script)
            return

        suffix = ''
        script = BOOT_SCRIPT % { 'rfs_ip': rfs_ip, 'suffix': suffix,
                                 'options': CFG['options'] }
        self.finish(script)


class RegisterHandler(tornado.web.RequestHandler):
    def get(self):
        self.content_type = 'text/plain; charset=utf-8'
        qs = self.request.query
        try:
            prologin.mdb.client.connect().register(qs)
        except prologin.mdb.client.RegistrationError as e:
            self.finish(REGISTER_ERROR_SCRIPT % { 'err': e.message })
        else:
            self.finish(REGISTER_DONE_SCRIPT)


prologin.log.setup_logging('netboot')

static_path = CFG['static_path']
application = tornado.wsgi.WSGIApplication([
    (r'/boot/(.*)/', BootHandler),
    (r'/register', RegisterHandler),
    (r'/static/(.*)', tornado.web.StaticFileHandler, { 'path': static_path }),
])

if __name__ == '__main__':
    import wsgiref.simple_server
    server = wsgiref.simple_server.make_server('', 8000, application)
    server.serve_forever()
