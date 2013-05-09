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
import subprocess
import sys
import requests

BASE_URL = 'http://minecraft/mylogin'


if __name__ == '__main__':
    try:
        os.chdir(os.path.expanduser('~/.minecraft/bin'))
    except OSError:
        print("Votre machine est mal configurée (~/.minecraft/bin n'existe pas)")
        sys.exit(1)

    print("Récupération du login...")
    r = requests.get(BASE_URL)
    if not r.ok:
        print("Votre machine n'est pas identifiable")
        sys.exit(2)

    login = r.content.decode('utf8')

    print("Démarage de Minecraft avec le login `%s`" % login)

    subprocess.call([
        'java',
        '-Xmx1024M',
        '-Xms512M',
        '-Duser.home=%s' % os.path.expanduser('~'),
        '-Djava.library.path=natives',
        '-classpath .',
        '-cp "*"',
        'net.minecraft.client.Minecraft',
        login,
        '0',
    ])
