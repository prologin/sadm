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
import requests
import yaml

from bottle import default_app, request, response, route, run, static_file
from prologin import mdb

BOOT_UNKNOWN_SCRIPT = """#!ipxe
echo An error occurred: netboot can't find the MAC in MDB.
echo Sleeping for 30s and rebooting.
sleep 30
reboot
"""

BOOT_SCRIPT = """#!ipxe
echo Booting the kernel on rfs-%(rfs)d:/nfsroot
kernel http://netboot/kernel/
initrd http://netboot/initrd/
boot rfs=%(rfs)d %(options)s
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

CFG = yaml.load(open(os.environ.get('NETBOOT_CONFIG',
                                   '/etc/prologin/netboot.yml')))

@route('/boot/<mac>/')
def boot(mac):
    response.content_type = 'text/plain; charset=utf-8'
    # TODO(delroth): This is blocking - not perfect... should be fast though.
    machine = mdb.connect().query(mac=mac)
    if len(machine) != 1:
        return BOOT_UNKNOWN_SCRIPT
    machine = machine[0]
    return BOOT_SCRIPT % { 'rfs': machine['rfs'],
                           'options': CFG.get('options', '') }

@route('/register')
def register():
    response.content_type = 'text/plain; charset=utf-8'
    qs = request.query_string
    r = requests.get(CFG.get('mdb', 'http://mdb/') + 'register?' + qs)
    if r.status_code != 200:
        return REGISTER_ERROR_SCRIPT % { 'err': r.text }
    else:
        return REGISTER_DONE_SCRIPT

@route('/kernel')
def kernel():
    return static_file(CFG.get('kernel'))

@route('/initrd')
def initrd():
    return static_file(CFG.get('initrd'))

application = default_app()
if __name__ == '__main__':
    run(host='localhost', port=8081)
