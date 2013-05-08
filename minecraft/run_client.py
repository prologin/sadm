#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Alexandre `Zopieux` Macabies <web@zopieux.com>
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

import os
import socket
import subprocess
import prologin.presenced


def run_minecraft():
    os.chdir(os.path.expanduser('~/.minecraft'))
    nick = prologin.presenced.ip_to_nick(socket.gethostname())
    subprocess.call([
        'java',
        '-Xmx1024M',
        '-Xms512M',
        # '-Duser.home=%s' % os.path.expanduser('~'),
        '-Djava.library.path=natives',
        '-classpath .',
        '-cp "*"',
        'net.minecraft.client.Minecraft',
        nick,
        '421337',
    ])


if __name__ == '__main__':
    run_minecraft()
