#!/usr/bin/env python3

# Copyright (c) 2016 Antoine Pietri <antoine.pietri@prologin.org>
# Copyright (c) 2016 Association Prologin <info@prologin.org>
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

import os
import re
import subprocess
import sys

def run(cmd, **kwargs):
    # Get the current display
    for f in os.listdir('/tmp/.X11-unix'):
        m = re.match(r'X([0-9]+)', f)
        if m is not None:
            display = ':' + m.group(1)

    # Get the XAUTHORITY cookie
    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
    for pid in pids:
        try:
            cmdline = open(os.path.join('/proc', pid, 'cmdline')).read()
        except IOError:
            continue
        cmdline = cmdline.split('\x00')
        if '/usr/lib/Xorg' not in cmdline[0]:
            continue
        xauthority = cmdline[cmdline.index('-auth') + 1]

    env = os.environ.copy()
    env['DISPLAY'] = display
    env['XAUTHORITY'] = xauthority
    print(cmd, env)
    subprocess.run(cmd, **kwargs, env=env)

if __name__ == '__main__':
    run(sys.argv[1:])
