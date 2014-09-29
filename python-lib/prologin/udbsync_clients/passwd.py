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

import collections
import datetime
import functools
import logging
import os
import prologin.config
import prologin.log
import prologin.presenced.client
import prologin.udbsync.client
import re
import shutil
import subprocess
import sys

User = collections.namedtuple('User',
    'login password uid gid name home shell'
)
Group = collections.namedtuple('Group', 'name password gid members')

USER_PATTERN = re.compile(
    '(?P<login>[-a-z_0-9]+)'
    ':(?P<password>[^:]*)'
    ':(?P<uid>\d+)'
    ':(?P<gid>\d+)'
    ':(?P<name>.*)'
    ':(?P<home>[^:]+)'
    ':(?P<shell>[^:]+)$'
)

SHADOW_PATTERN = re.compile(
    '(?P<login>[-a-z_0-9]+):(?P<remainder>.*)$'
)

GROUP_PATTERN = re.compile(
    '(?P<name>[-a-z_0-9]+)'
    ':(?P<password>[^:]*)'
    ':(?P<gid>\d+)'
    ':(?P<members>[-a-z_0-9,]*)$'
)

PROLOGIN_GROUPS = {
    'user': 10000,
    'orga': 10001,
}
PASSWD_PERMS    = 0o644
SHADOW_PERMS    = 0o600
GROUP_PERMS     = 0o644

HOME_DIR = '/home/{}'


class BufferFile:
    """Write to `filepath` using a temporary file as a buffer, so that the
    destination file is changed instantly.
    """
    def __init__(self, filepath, perms):
        self.filepath = filepath
        self.temp_path = os.path.join(
            '/tmp',
            filepath.replace(os.path.sep, '-')
        )
        self.f = open(self.temp_path, 'w')
        os.chmod(self.temp_path, perms)

    def __enter__(self):
        return self.f

    def __exit__(self, type, value, traceback):
        self.f.close()
        shutil.move(self.temp_path, self.filepath)

def callback(root_path, users, updates_metadata):
    logging.info('New updates: {!r}'.format(updates_metadata))

    passwd_users = {}
    shadow_passwords = {}
    groups = {}

    # First, parse /etc/passwd to get users that are not handled by Prologin.
    with open(os.path.join(root_path, 'etc/passwd'), 'r') as f:
        for line in f:
            line = line.rstrip('\n')
            m = USER_PATTERN.match(line)
            if m:
                user = User(
                    m.group('login'),
                    m.group('password'),
                    int(m.group('uid')),
                    int(m.group('gid')),
                    m.group('name'),
                    m.group('home'),
                    m.group('shell'),
                )
                if not prologin.presenced.client.is_prologin_uid(user.uid):
                    passwd_users[user.login] = user
            else:
                logging.error('Unparsable /etc/passwd line: {!r}'.format(line))
                logging.info('Stopping generation')
                return

    # Then, parse /etc/shadow to get passwords.
    with open(os.path.join(root_path, 'etc/shadow'), 'r') as f:
        for line in f:
            line = line.rstrip('\n')
            m = SHADOW_PATTERN.match(line)
            if m:
                shadow_passwords[m.group('login')] = m.group('remainder')
            else:
                logging.error('Unparsable /etc/passwd line: {!r}'.format(line))
                logging.info('Stopping generation')
                return

    # Parse /etc/group to get... groups!
    with open(os.path.join(root_path, 'etc/group'), 'r') as f:
        for line in f:
            line = line.rstrip('\n')
            m = GROUP_PATTERN.match(line)
            if m:
                name = m.group('name')
                groups[name] = Group(
                    name, m.group('password'),
                    int(m.group('gid')),
                    set(
                        member
                        for member in m.group('members').split(',')
                        if member
                    )
                )
            else:
                logging.error('Unparsable /etc/group line: {!r}'.format(line))
                logging.info('Stopping generation')
                return

    # Reset prologin groups.
    for name, gid in PROLOGIN_GROUPS.items():
        try:
            group = groups[name]
        except KeyError:
            # If it does not exist, create it.
            # TODO: check that there is no existing group with the same GID.
            groups[name] = Group(name, 'x', gid, set())
        else:
            groups[name].members.clear()

    # Complete with users handled by Prologin.
    days_since_epoch = (
        datetime.datetime.today() - datetime.datetime(1970, 1, 1)
    ).days
    for login, udb_user in users.items():
        utype_to_groups = {
            'user': ['user'],
            'orga': ['orga', 'user'],
            'root': ['orga', 'user'],
        }
        user_groups = utype_to_groups[udb_user['group']]
        user = User(
            udb_user['login'], 'x',
            udb_user['uid'], PROLOGIN_GROUPS[user_groups[0]],
            udb_user['firstname'] + ' ' + udb_user['lastname'],
            HOME_DIR.format(udb_user['login']), udb_user['shell'],
        )
        passwd_users[login] = user

        # Shadow fields:
        # - login (here: the key of the dict)
        # - hash (generated using openssl(1))
        # - days between Epoch and last time password changed (today)
        # - number of days before changing is allowed (0)
        # - number of days the password is valid (tons of days)
        # - number of days before password expiration for warnings (0)
        # - number of days after password expiration for account disabling (0)
        password = subprocess.check_output(
            ['openssl', 'passwd', '-1', udb_user['password']]
        ).decode('ascii').strip()
        shadow_passwords[login] = '{}:{}:0:99999:7:0::'.format(
            password, days_since_epoch
        )

        for name in user_groups:
            groups[name].members.add(udb_user['login'])

    userless_shadows = set(shadow_passwords) - set(passwd_users)
    shadowless_users = set(passwd_users) - set(shadow_passwords)
    if userless_shadows:
        logging.error('Some shadow passwords have no passwd users: {}'.format(
            ', '.join(userless_shadows)
        ))
        logging.info('Stopping generation')
        return
    if shadowless_users:
        logging.error('Some passwd users have no shadow passord: {}'.format(
            ', '.join(shadowless_users)
        ))
        logging.info('Stopping generation')
        return

    # TODO: moar consistency checks!

    sorted_users = list(passwd_users.values())
    sorted_users.sort(key=lambda u: u.uid)

    sorted_groups = list(groups.values())
    sorted_groups.sort(key=lambda g: g.gid)

    # Finally, output updated files.
    with BufferFile(os.path.join(root_path, 'etc/passwd'), PASSWD_PERMS) as f:
        for user in sorted_users:
            print(
                '{0.login}:{0.password}'
                ':{0.uid}:{0.gid}'
                ':{0.name}'
                ':{0.home}:{0.shell}'.format(user),
                file=f
            )

    with BufferFile(os.path.join(root_path, 'etc/shadow'), SHADOW_PERMS) as f:
        for user in sorted_users:
            try:
                shadow = shadow_passwords[user.login]
            except KeyError:
                pass
            else:
                print('{}:{}'.format(user.login, shadow), file=f)

    with BufferFile(os.path.join(root_path, 'etc/group'), GROUP_PERMS) as f:
        for group in sorted_groups:
            print(
                '{0.name}:{0.password}:{0.gid}:{1}'.format(
                    group, ','.join(sorted(
                        group.members, key=lambda m: passwd_users[m].uid
                    ))
                ),
                file=f
            )


if __name__ == '__main__':
    if len(sys.argv) != 2:
        root_path = '/'
    else:
        root_path = sys.argv[1]
    prologin.log.setup_logging('udbsync_passwd({})'.format(root_path))
    callback = functools.partial(callback, root_path)
    prologin.udbsync.client.connect().poll_updates(callback)
