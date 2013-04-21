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


"""Installation script for the components of Prologin SADM.

Handles upgrades as well, including configuration upgrades (creates a .new file
and alerts the root that a merge is required).

This can NOT use prologin.* packages as they are most likely not yet installed!
"""

import contextlib
import grp
import os
import os.path
import pwd
import shutil
import sys

# It's better to have a consistent user<->uid mapping. We keep it here.
USERS = {
    'mdb': { 'uid': 20000, 'groups': ('mdb', 'mdb_public', 'mdbsync',
                                      'mdbsync_public') },
    'mdbsync': { 'uid': 20010, 'groups': ('mdbsync', 'mdbsync_public',
                                          'mdb_public') },
    'netboot': { 'uid': 20020, 'groups': ('netboot', 'mdb_public') },
    'mdbdns': { 'uid': 20030, 'groups': ('mdbdns', 'mdbsync_public') },
    'mdbdhcp': { 'uid': 20040, 'groups': ('mdbdhcp', 'mdbsync_public') },
}

# Same with groups. *_public groups are used for services that need to access
# the public API for the services.
GROUPS = {
    'mdb': 20000,
    'mdb_public': 20001,
    'mdbsync': 20010,
    'mdbsync_public': 20011,
    'netboot': 20020,
    'mdbdns': 20030,
    'mdbdhcp': 20040,
}

# Helper functions for installation procedures.

@contextlib.contextmanager
def cwd(path):
    """Moves to a directory relative to the current script."""
    dirpath = os.path.abspath(os.path.dirname(__file__))
    os.chdir(os.path.join(dirpath, path))
    yield
    os.chdir(dirpath)


def mkdir(path, mode):
    if os.path.exists(path):
        os.chmod(path, mode)
    else:
        os.mkdir(path, mode)


CFG_TO_REVIEW = []
def install_cfg(path, dest_dir, owner='root:root', mode=0o600):
    user, group = owner.split(':')
    dest_path = os.path.join(dest_dir, os.path.basename(path))

    if os.path.exists(dest_path):
        old_contents = open(dest_path).read()
        new_contents = open(path).read()
        if old_contents == new_contents:
            return
        CFG_TO_REVIEW.append(dest_path)
        dest_path += '.new'

    print('Copying configuration %r -> %r' % (path, dest_path))
    shutil.copy(path, dest_path)
    shutil.chown(dest_path, user, group)
    os.chmod(dest_path, mode)


def install_cfg_profile(name, group):
    mkdir('/etc/prologin', mode=0o755)
    install_cfg(os.path.join('config', name + '.yml'), '/etc/prologin',
                owner='root:%s' % group, mode=0o640)


def install_nginx_service(name):
    install_cfg(os.path.join('nginx', 'services', name + '.nginx'),
                '/etc/nginx/services', owner='root:root', mode=0o644)


def install_systemd_unit(name):
    install_cfg(os.path.join('systemd', name + '.service'),
                '/etc/systemd/system', owner='root:root', mode=0o644)


def install_service_dir(name, owner, mode):
    if not os.path.exists('/var/prologin'):
        mkdir('/var/prologin', mode=0o755)
    # Nothing in Python allows merging two directories together...
    os.system('cp -rv %s /var/prologin' % name)
    user, group = owner.split(':')
    shutil.chown('/var/prologin/%s' % name, user, group)
    os.chmod('/var/prologin/%s' % name, mode)


def django_syncdb(name, user=None):
    if user is None:
        user = name

    with cwd('/var/prologin/%s' % name):
        cmd = 'su -c "/var/prologin/venv/bin/python manage.py syncdb" '
        cmd += user
        os.system(cmd)

# Component specific installation procedures

def install_libprologin():
    with cwd('python-lib'):
        os.system('python setup.py install')

    install_cfg_profile('mdb-client', group='mdb_public')
    install_cfg_profile('mdbsync-sub', group='mdbsync_public')


def install_nginxcfg():
    install_cfg('nginx/nginx.conf', '/etc/nginx', owner='root:root',
                mode=0o644)
    mkdir('/etc/nginx/services', mode=0o755)


def install_mdb():
    requires('libprologin')
    requires('nginxcfg')

    first_time = os.path.exists('/var/prologin/mdb')

    install_service_dir('mdb', owner='mdb:mdb', mode=0o700)
    install_nginx_service('mdb')
    install_systemd_unit('mdb')

    install_cfg_profile('mdb-server', group='mdb')

    if first_time:
        django_syncdb('mdb')


COMPONENTS = [
    'libprologin',
    'nginxcfg',
    'mdb',
]

# Runtime helpers: requires() function and user/groups handling

def requires(component):
    """Runs the installation function of the component."""

    print('Installing %r' % component)

    if component not in COMPONENTS:
        raise RuntimeError('invalid component %r' % component)

    globals()['install_' + component]()


def sync_groups():
    """Installs all the required groups if they are not yet present."""

    for (gr, gid) in GROUPS.items():
        try:
            grp.getgrnam(gr)
        except KeyError:
            print('Creating group %r' % gr)
            os.system('groupadd -g %d %s' % (gid, gr))


def sync_users():
    """Installs all the required users and checks for groups membership."""

    for (user, data) in USERS.items():
        main_grp = data['groups'][0]
        other_grps = data['groups'][1:]
        try:
            entry = pwd.getpwnam(user)
            cmd = 'usermod -g %s' % main_grp
            if other_grps:
                cmd += ' -G %s' % ','.join(other_grps)
            cmd += ' ' + user
            os.system(cmd)
        except KeyError:
            print('Creating user %r' % user)
            uid = data['uid']

            cmd = 'useradd -d /var/empty -M -N -u %d -g %s' % (uid, main_grp)
            if other_grps:
                cmd += ' -G %s' % ','.join(other_grps)
            cmd += ' ' + user
            os.system(cmd)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('usage: python3 install.py <component> [components...]')
        print('Components:')
        for name in sorted(COMPONENTS):
            print(' - %s' % name)
        sys.exit(1)

    if os.getuid() != 0:
        print('error: this script needs to be run as root')
        sys.exit(1)

    sync_groups()
    sync_users()

    try:
        for name in sys.argv[1:]:
            requires(name)
    except RuntimeError as e:
        print('error: ' + str(e))
        sys.exit(1)

    if CFG_TO_REVIEW:
        print('WARNING: The following configuration files need to be merged:')
        for cfg in CFG_TO_REVIEW:
            print(' - %s' % cfg)
