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
echo Booting the kernel on %(rfs_ip)s:/nfsroot_ro
initrd http://netboot/static/initrd%(suffix)s
boot http://netboot/static/kernel%(suffix)s nfsroot=%(rfs_ip)s:/export/nfsroot_ro,ro %(options)s
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

BOOT_FAULTY_SCRIPT = """#!ipxe
echo ERROR: This machine was marked as faulty.
echo Reason: {}
echo
sleep 60
reboot
"""


class BootHandler(tornado.web.RequestHandler):
    """Send the initrd and kernel urls to registered machines."""

    def get(self, mac):
        self.content_type = 'text/plain; charset=utf-8'
        # TODO(delroth): This is blocking - not perfect... should be fast
        # though.
        machine = prologin.mdb.client.connect().query(mac=mac)
        if len(machine) != 1:
            self.finish(BOOT_UNKNOWN_SCRIPT)
            return

        machine = machine[0]
        if machine['is_faulty']:
            self.finish(
                BOOT_FAULTY_SCRIPT.format(machine['is_faulty_details'])
            )
            return

        rfs_hostname = 'rfs%d' % machine['rfs']
        rfs = prologin.mdb.client.connect().query(
            aliases__contains=rfs_hostname
        )
        try:
            rfs_ip = rfs[0]['ip']
        except IndexError:
            script = REGISTER_ERROR_SCRIPT % {
                'err': 'No such RFS: %s' % rfs_hostname
            }
            self.finish(script)
            return

        suffix = ''
        script = BOOT_SCRIPT % {
            'rfs_ip': rfs_ip,
            'suffix': suffix,
            'options': CFG['options'],
        }
        self.finish(script)


class BootstrapHandler(tornado.web.RequestHandler):
    """Send the base IPXE script with switches names for LLDP.

       This is the expected format (sw_name_X is the corresponding switch
       chassis ID):

       set sw_name_0 02:99:71:f6:c6:5a
       set sw_rfs_0  0
       set sw_hfs_0  0
       set sw_room_0 pasteur

       set sw_name_1 02:99:71:f6:c6:5b
       set sw_rfs_1  1
       set sw_hfs_1  1
       set sw_room_1 alt
    """

    def get(self):
        self.content_type = 'text/plain; charset=utf-8'
        code_dir = os.path.abspath(os.path.dirname(__file__))
        creation_script = os.path.join(code_dir, 'script.ipxe')
        switches = prologin.mdb.client.connect().switches()

        fragments = []
        for i, s in enumerate(switches):
            fragment = (
                'set sw_name_{count} {chassis}\n'
                'set sw_rfs_{count} {rfs}\n'
                'set sw_hfs_{count} {hfs}\n'
                'set sw_room_{count} {room}'
            ).format(
                count=i,
                chassis=s['chassis'],
                rfs=s['rfs'],
                hfs=s['hfs'],
                room=s['room'],
            )
            fragments.append(fragment)

        with open(creation_script) as script:
            content = script.read()
            content = content.replace(
                '#%%NETBOOT_REPLACE_SWITCH_INFO%%', '\n\n'.join(fragments)
            )
            self.finish(content)


class RegisterHandler(tornado.web.RequestHandler):
    """Register an alien machine in mdb."""

    def get(self):
        self.content_type = 'text/plain; charset=utf-8'
        try:
            kwargs = {
                'hostname': self.get_query_argument('hostname'),
                'mac': self.get_query_argument('mac'),
                'rfs': int(self.get_query_argument('rfs')),
                'hfs': int(self.get_query_argument('hfs')),
                'room': self.get_query_argument('room'),
                'mtype': self.get_query_argument('mtype'),
            }
            prologin.mdb.client.connect().register(**kwargs)
        except Exception as e:
            try:
                message = e.message
            except AttributeError:
                message = str(e)
            self.finish(REGISTER_ERROR_SCRIPT % {'err': message})
        else:
            self.finish(REGISTER_DONE_SCRIPT)


prologin.log.setup_logging('netboot')

static_path = CFG['static_path']
application = tornado.wsgi.WSGIApplication(
    [
        (r'/boot/(.*)/', BootHandler),
        (r'/bootstrap', BootstrapHandler),
        (r'/register', RegisterHandler),
        (
            r'/static/(.*)',
            tornado.web.StaticFileHandler,
            {'path': static_path},
        ),
    ]
)

if __name__ == '__main__':
    import wsgiref.simple_server

    server = wsgiref.simple_server.make_server('', 8000, application)
    server.serve_forever()
