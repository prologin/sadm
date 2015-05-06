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
import errno
import grp
import os
import os.path
import pwd
import re
import shutil
import sys

# It's better to have a consistent user<->uid mapping. We keep it here.
USERS = {
    'mdb': { 'uid': 20000, 'groups': ('mdb', 'mdb_public', 'mdbsync',
                                      'mdbsync_public', 'udbsync_public') },
    'mdbsync': { 'uid': 20010, 'groups': ('mdbsync', 'mdbsync_public',
                                          'mdb_public') },
    'netboot': { 'uid': 20020, 'groups': ('netboot', 'mdb_public') },
    'mdbdns': { 'uid': 20030, 'groups': ('mdbdns', 'mdbsync_public') },
    'mdbdhcp': { 'uid': 20040, 'groups': ('mdbdhcp', 'mdbsync_public') },
    'webservices': { 'uid': 20050, 'groups': ('webservices',) },
    'presencesync': { 'uid': 20060, 'groups': ('presencesync',
                                               'presencesync_public',
                                               'mdb_public', 'udb_public') },
    'presenced': { 'uid': 20070, 'groups': ('presenced',
                                            'presencesync',
                                            'presencesync_public') },
    'udb': { 'uid': 20080, 'groups': ('udb', 'udb_public', 'udbsync',
                                      'udbsync_public') },
    'udbsync': { 'uid': 20090, 'groups': ('udbsync', 'udbsync_public',
                                          'udb', 'udb_public') },
    'hfs': { 'uid': 20100, 'groups': ('hfs', 'hfs_public') },
    'homepage': { 'uid': 20110, 'groups': ('homepage', 'udbsync_public') },
    'redmine': { 'uid': 20120, 'groups': ('redmine', 'udbsync_public') },
    'presencesync_usermap': { 'uid': 20130,
                              'groups': ('presencesync_usermap',
                                         'presencesync_public',
                                         'udb_public') },
    'presencesync_cacheserver': { 'uid': 20131,
                                  'groups': ('presencesync_cacheserver',
                                             'presencesync_public',
                                             'udb_public', 'mdb_public') },
    'minecraft': { 'uid': 20140, 'groups': ('minecraft',) },  # FIXME: needs presencesync?
    'concours': { 'uid': 20150, 'groups': ('concours', 'udbsync_public',
                                           'cluster_public') },
    'cluster': { 'uid': 20160, 'groups': ('cluster', 'cluster_public') },
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
    'webservices': 20050,
    'presencesync': 20060,
    'presencesync_public': 20061,
    'presenced': 20070,
    'udb': 20080,
    'udb_public': 20081,
    'udbsync': 20090,
    'udbsync_public': 20091,
    'hfs': 20100,
    'hfs_public': 20101,
    'homepage': 20110,
    'redmine': 20120,
    'presencesync_usermap': 20130,
    'presencesync_cacheserver': 20131,
    'minecraft': 20140,  # FIXME: needs _public?
    'concours': 20150,
    'cluster': 20160,
    'cluster_public': 20161,
}


# Helper functions for installation procedures.

@contextlib.contextmanager
def cwd(path):
    """Moves to a directory relative to the current script."""
    dirpath = os.path.abspath(os.path.dirname(__file__))
    os.chdir(os.path.join(dirpath, path))
    yield
    os.chdir(dirpath)


def mkdir(path, mode, owner='root:root'):
    if os.path.exists(path):
        os.chmod(path, mode)
    else:
        os.mkdir(path, mode)
    user, group = owner.split(':')
    shutil.chown(path, user, group)


def copy(old, new, mode=0o600, owner='root:root'):
    print('Copying %s -> %s (mode: %o) (own: %s)' % (old, new, mode, owner))
    shutil.copy(old, new)
    os.chmod(new, mode)
    user, group = owner.split(':')
    shutil.chown(new, user, group)


def copytree(old, new, dir_mode=0o700, file_mode=0o600, owner='root:root'):
    print('Copying %s -> %s (file mode: %o) (dir mode: %o) (own: %s)' % (old, new, file_mode, dir_mode, owner))
    shutil.copytree(old, new)
    user, group = owner.split(':')
    for root, dirs, files in os.walk(new):
        for momo in dirs:
            path = os.path.join(root, momo)
            os.chmod(path, dir_mode)
            shutil.chown(path, user, group)
        for momo in files:
            path = os.path.join(root, momo)
            os.chmod(path, file_mode)
            shutil.chown(path, user, group)


def symlink(dest, path):
    print('Creating symlink %s -> %s' % (path, dest))
    try:
        os.symlink(dest, path)
    except OSError as e:
        if e.errno == errno.EEXIST:
            os.remove(path)
            os.symlink(dest, path)


def system(command):
    print('Executing "%s"' % command)
    return os.system(command)


NEW_CFG = []
CFG_TO_REVIEW = []
def install_cfg(path, dest_dir, owner='root:root', mode=0o600):
    dest_path = os.path.join(dest_dir, os.path.basename(path))
    src_path = os.path.join('etc', path)

    if os.path.exists(dest_path):
        old_contents = open(dest_path).read()
        new_contents = open(src_path).read()
        if old_contents == new_contents:
            return
        CFG_TO_REVIEW.append(dest_path)
        dest_path += '.new'
    else:
        NEW_CFG.append(dest_path)

    copy(src_path, dest_path, mode=0o640, owner=owner)
    os.chmod(dest_path, mode)


def install_cfg_profile(name, group, mode=0o640):
    mkdir('/etc/prologin', mode=0o755, owner='root:root')
    install_cfg(os.path.join('prologin', name + '.yml'),
            '/etc/prologin', owner='root:%s' % group, mode=mode)


def install_nginx_service(name, contest=False):
    if contest:
        where = '/etc/nginx/services_contest'
    else:
        where = '/etc/nginx/services'
    install_cfg(os.path.join('nginx', 'services', name + '.nginx'),
                where, owner='root:root', mode=0o644)


def install_systemd_unit(name, instance='system', kind='service'):
    install_cfg(os.path.join('systemd', instance, name + '.' + kind),
                '/etc/systemd/' + instance , owner='root:root', mode=0o644)


def install_service_dir(path, owner, mode):
    if not os.path.exists('/var/prologin'):
        mkdir('/var/prologin', mode=0o755, owner='root:root')
    name = os.path.basename(path)  # strip service kind from path (eg. django)
    # Nothing in Python allows merging two directories together...
    # Be careful with rsync(1) arguments: to merge two directories, trailing
    # slash are meaningful.
    system('rsync -rv %s/ /var/prologin/%s' % (path, name))
    user, group = owner.split(':')

    shutil.chown('/var/prologin/%s' % name, user, group)
    os.chmod('/var/prologin/%s' % name, mode)
    for root, dirs, files in os.walk('/var/prologin/%s' % name):
        for dir in dirs:
            shutil.chown(os.path.join(root, dir), user, group)
            os.chmod(os.path.join(root, dir), mode)
        for file in files:
            shutil.chown(os.path.join(root, file), user, group)
            os.chmod(os.path.join(root, file), mode)


def django_migrate(name, user=None):
    if user is None:
        user = name

    with cwd('/var/prologin/%s' % name):
        cmd = 'su -c "/var/prologin/venv/bin/python manage.py migrate --noinput" '
        cmd += user
        system(cmd)


def check_database_exists(database):
    retcode = system("exit $(echo \"SELECT 1 FROM pg_database WHERE datname='{}'\" | "
                     "su - postgres -c 'psql -t')"
                     .format(database))
    return retcode != 0


def execute_sql(name, database=None, verbose=True):
    """
    Executes SQL commands in file sql/`name`.sql on database `database`
    (if provided).
    """
    path = os.path.join('sql', '{}.sql'.format(name))
    args = []
    if verbose:
        args.append('--set VERBOSITY=verbose')
    if database:
        args.append(database)

    system("su - postgres -c 'psql {args}' < {path}".format(
        path=path,
        args=' '.join(args),
    ))


# Component specific installation procedures

def install_libprologin():
    with cwd('python-lib'):
        system('python setup.py --quiet install')

    install_cfg_profile('hfs-client', group='hfs_public')
    install_cfg_profile('mdb-client', group='mdb_public')
    install_cfg_profile('mdbsync-pub', group='mdbsync')
    install_cfg_profile('mdbsync-sub', group='mdbsync_public')
    install_cfg_profile('presenced-client', group='presenced')
    install_cfg_profile('presencesync-pub', group='presencesync')
    install_cfg_profile('presencesync-sub', group='presencesync_public')
    install_cfg_profile('timeauth', group='root', mode=0o644)
    install_cfg_profile('udb-client', group='udb_public')
    install_cfg_profile('udb-client-auth', group='udb')
    install_cfg_profile('udbsync-pub', group='udbsync')
    install_cfg_profile('udbsync-sub', group='udbsync_public')


def install_nginxcfg():
    install_cfg('nginx/nginx.conf', '/etc/nginx', owner='root:root',
                mode=0o644)
    install_cfg('nginx/proxy_params', '/etc/nginx', owner='root:root',
                mode=0o644)
    install_cfg('nginx/long_polling', '/etc/nginx', owner='root:root',
                mode=0o644)
    install_cfg('nginx/enable_sso', '/etc/nginx', owner='root:root',
                mode=0o644)
    if not os.path.exists('/etc/nginx/sso'):
        copytree('etc/nginx/sso', '/etc/nginx/sso', owner='http:root',
                 dir_mode=0o750, file_mode=0o640)
    mkdir('/etc/nginx/services', mode=0o755, owner='root:root')
    mkdir('/etc/nginx/services_contest', mode=0o755, owner='root:root')
    if not os.path.exists('/etc/nginx/logs'):
        mkdir('/var/log/nginx', mode=0o750, owner='http:log')
        symlink('/var/log/nginx', '/etc/nginx/logs')


def install_bindcfg():
    install_cfg('named.conf', '/etc', owner='root:named', mode=0o640)
    mkdir('/etc/named', mode=0o770, owner='named:mdbdns')
    for zone in ('0.in-addr.arpa', '127.in-addr.arpa', '255.in-addr.arpa',
                 'localhost'):
        install_cfg('named/%s.zone' % zone, '/etc/named',
                    owner='named:named', mode=0o640)
    install_cfg('named/root.hint', '/etc/named', owner='named:named',
                mode=0o640)
    shutil.chown('/etc/rndc.key', 'named', 'mdbdns')
    install_systemd_unit('named')


def install_dhcpdcfg():
    install_cfg('dhcpd.conf', '/etc', owner='root:root', mode=0o640)
    mkdir('/etc/dhcpd', mode=0o770, owner='root:mdbdhcp')


def install_sshdcfg():
    install_cfg('ssh/sshd_config', '/etc/ssh', owner='root:root', mode=0o644)


def install_mdb():
    requires('libprologin')
    requires('nginxcfg')

    db_exists = check_database_exists('mdb')

    install_service_dir('django/mdb', owner='mdb:mdb', mode=0o700)
    install_nginx_service('mdb')
    install_systemd_unit('mdb')

    install_cfg_profile('mdb-server', group='mdb')
    install_cfg_profile('mdb-udbsync', group='mdb')

    if not db_exists:
        execute_sql('mdb')
        django_migrate('mdb')

    mkdir('/etc/ansible', mode=0o755, owner='root:root')
    install_cfg('ansible/hosts', '/etc/ansible/', mode=0o700)


def install_mdbsync():
    requires('libprologin')
    requires('nginxcfg')

    install_nginx_service('mdbsync')
    install_systemd_unit('mdbsync')


def install_mdbdns():
    requires('libprologin')
    requires('bindcfg')

    install_systemd_unit('mdbdns')


def install_mdbdhcp():
    requires('libprologin')
    requires('dhcpdcfg')

    install_systemd_unit('mdbdhcp')


def install_docs():
    requires('nginxcfg')

    install_service_dir('webservices/docs', mode=0o755,
                        owner='webservices:http')
    install_nginx_service('docs')

def install_paste():
    requires('nginxcfg')

    # TODO: use the appropriate database_exists check
    first_time = not os.path.exists('/var/prologin/mdb')

    install_service_dir('webservices/paste', mode=0o755,
                        owner='webservices:http')
    install_nginx_service('paste')
    install_systemd_unit('paste')

    if first_time:
        # Use specific venv
        with cwd('/var/prologin/paste'):
            cmd = 'su -c "/var/prologin/venv_paste/bin/python manage.py migrate --noinput" '
            cmd += 'webservices'
            system(cmd)


def install_redmine():
    requires('libprologin')
    requires('nginxcfg')

    copy(
        'webservices/redmine/unicorn.ru',
        '/var/prologin/redmine/script/unicorn.ru',
        owner='redmine:redmine', mode=0o640
    )
    copy(
        'webservices/redmine/user_update.rb',
        '/var/prologin/redmine/script/user_update.rb',
        owner='redmine:redmine', mode=0o640
    )
    copytree(
        'webservices/redmine/issues_json_socket_send',
        '/var/prologin/redmine/plugins/issues_json_socket_send',
        owner='redmine:redmine', dir_mode=0o750, file_mode=0o640
    )

    install_nginx_service('redmine', contest=True)
    install_systemd_unit('redmine')


def install_irc_redmine_issues():
    requires('redmine')

    install_systemd_unit('irc_redmine_issues')
    install_cfg_profile('irc-redmine-issues', group='redmine')


def install_homepage():
    requires('libprologin')
    requires('udbsync_django')
    requires('nginxcfg')

    db_exists = check_database_exists('homepage')

    install_service_dir('django/homepage', owner='homepage:homepage',
                        mode=0o700)
    install_nginx_service('homepage')
    install_systemd_unit('homepage')

    install_cfg_profile('homepage', group='homepage')
    install_cfg_profile('homepage-udbsync', group='homepage')

    if not db_exists:
        execute_sql('homepage')
        django_migrate('homepage')


def install_concours():
    requires('libprologin')
    requires('udbsync_django')
    requires('nginxcfg')

    db_exists = check_database_exists('concours')

    install_service_dir('django/concours', owner='concours:concours',
            mode=0o700)
    install_nginx_service('concours', contest=True)
    install_systemd_unit('concours')

    install_cfg_profile('concours', group='concours')
    install_cfg_profile('concours-udbsync', group='concours')

    if not db_exists:
        execute_sql('concours')
        django_migrate('concours')


def install_netboot():
    requires('libprologin')
    requires('nginxcfg')

    install_nginx_service('netboot')
    install_systemd_unit('netboot')
    install_cfg_profile('netboot', group='netboot')


def install_udb():
    requires('libprologin')
    requires('nginxcfg')

    db_exists = check_database_exists('udb')

    install_service_dir('django/udb', owner='udb:udb', mode=0o700)
    install_nginx_service('udb')
    install_systemd_unit('udb')

    install_cfg_profile('udb-server', group='udb')
    install_cfg_profile('udb-udbsync', group='udb')

    if not db_exists:
        execute_sql('udb')
        django_migrate('udb')


def install_udbsync():
    requires('libprologin')
    requires('nginxcfg')

    install_nginx_service('udbsync')
    install_systemd_unit('udbsync')


def install_udbsync_django():
    requires('libprologin')
    requires('udbsync')

    install_systemd_unit('udbsync_django@')


def install_udbsync_passwd():
    requires('libprologin')

    install_systemd_unit('udbsync_passwd')


def install_udbsync_redmine():
    requires('libprologin')

    install_systemd_unit('udbsync_redmine')


def install_udbsync_rfs():
    requires('libprologin')
    requires('udbsync_rootssh')

    install_systemd_unit('udbsync_passwd_nfsroot')
    install_systemd_unit('rootssh-copy')
    install_systemd_unit('rootssh', kind='path')


def install_udbsync_rootssh():
    requires('libprologin')

    install_systemd_unit('udbsync_rootssh')


def install_presenced():
    requires('libprologin')
    requires('nginxcfg')

    install_service_dir('python-lib/prologin/presenced',
                        owner='presenced:presenced', mode=0o700)
    install_systemd_unit('presenced')

    cfg = '/etc/pam.d/system-login'
    cfg_line = (
        'session requisite pam_exec.so'
        ' /var/prologin/presenced/pam_presenced.py'
    )

    cfg_contents = []
    with open(cfg, 'r') as f:
        cfg_contents = f.read().split('\n')
        to_append = cfg_line not in cfg_contents

    if to_append:
        cfg_contents = '\n'.join(cfg_contents)
        cfg_new = re.sub(r'(.*pam_systemd.*)', cfg_line + r'\n\1', cfg_contents)
        with open(cfg, 'w') as f:
            print(cfg_new, file=f)


def install_presencesync():
    requires('libprologin')
    requires('nginxcfg')

    install_service_dir('python-lib/prologin/presencesync',
                        owner='presencesync:presencesync',
                        mode=0o700)
    install_nginx_service('presencesync')
    install_systemd_unit('presencesync')


def install_presencesync_usermap():
    requires('libprologin')

    install_cfg_profile('presencesync_usermap', group='presencesync_usermap')

    mkdir(
        '/var/prologin/presencesync_usermap',
        mode=0o700, owner='presencesync_usermap:presencesync_usermap'
    )
    copy(
        'python-lib/prologin/presencesync_clients/usermap.svg',
        '/var/prologin/presencesync_usermap/pattern.svg',
        mode=0o700, owner='presencesync_usermap:presencesync_usermap'
    )
    install_systemd_unit('presencesync_usermap')


def install_presencesync_cacheserver():
    requires('libprologin')

    install_systemd_unit('presencesync_cacheserver')


def install_presencesync_firewall():
    requires('libprologin')

    install_cfg_profile('presencesync_firewall', group='root')
    install_systemd_unit('presencesync_firewall')


def install_rfs():
    copy('etc/sysctl/rp_filter.conf', '/etc/sysctl.d/rp_filter.conf')
    system('systemctl restart systemd-sysctl')

    rootfs = '/export/nfsroot'
    subnet = '192.168.0.0/24'
    with cwd('rfs'):
        os.environ['ROOTFS'] = rootfs
        os.environ['SUBNET'] = subnet
        with open('packages_lists') as f:
            packages_lists = f.read()
        os.environ['PACKAGES'] = ' '.join(packages_lists.split())
        os.system('./init.sh')


def install_hfs():
    requires('libprologin')

    install_systemd_unit('hfs@')
    install_cfg_profile('hfs-server', group='hfs')

    if not os.path.exists('/export/skeleton'):
        copytree(
            'python-lib/prologin/hfs/skeleton',
            '/export/skeleton',
            dir_mode=0o755, file_mode=0o644,
            owner='root:root'
        )


def install_set_hostname():
    requires('libprologin')

    install_systemd_unit('set_hostname')


def install_resolved():
    symlink('/var/run/systemd/resolve/resolv.conf', '/etc/resolv.conf')


def install_networkd():
    for networkd_file in ['lan.link', 'lan.network', 'uplink.link',
                          'uplink.network']:
        copy('etc/systemd/network/' + networkd_file,
             '/etc/systemd/network/' + networkd_file,
             mode=0o644)
    symlink('/dev/null', '/etc/systemd/network/99-default.link')


def install_firewall():
    copy('etc/sysctl/ip_forward.conf', '/etc/sysctl.d/ip_forward.conf')
    system('systemctl restart systemd-sysctl')

    install_systemd_unit('firewall')
    install_cfg('iptables.save', '/etc/prologin/')


def install_masternode():
    requires('libprologin')
    install_systemd_unit('masternode')
    install_cfg_profile('masternode', group='concours')
    mkdir(
        '/var/prologin/concours_shared',
        mode=0o770,
        owner='concours:cluster_public'
    )
    mkdir(
        '/var/prologin/concours_shared/maps',
        mode=0o770,
        owner='concours:cluster_public'
    )


def install_workernode():
    requires('libprologin')
    install_systemd_unit('workernode')
    install_cfg_profile('workernode', group='cluster')


def install_minecraft():
    requires('libprologin')
    requires('nginxcfg')
    requires('presencesync')

    install_cfg_profile('minecraft', group='minecraft')

    mkdir(
        '/var/prologin/minecraft',
        mode=0o755, owner='minecraft:minecraft'
    )

    copytree(
        'minecraft/static',
        '/var/prologin/minecraft/static',
        dir_mode=0o755, file_mode=0o644,
        owner='minecraft:minecraft'
    )

    mkdir(
        '/var/prologin/minecraft/static/resources',
        mode=0o755, owner='minecraft:minecraft'
    )

    copytree(
        'minecraft/server',
        '/var/prologin/minecraft/server',
        dir_mode=0o700, file_mode=0o600,
        owner='minecraft:minecraft'
    )

    with cwd('/var/prologin/minecraft'):
        # download static resources once (this takes time!)
        # and create shared servers.dat
        os.system('python setup.py')

    install_nginx_service('minecraft-skins')
    install_nginx_service('minecraft')

    install_systemd_unit('minecraft-skins')
    install_systemd_unit('minecraft')

    # TODO:
    # for each user machine:
    #   mkdir ~/.minecraft
    #   ln -s /var/prologin/minecraft/static/bin ~/.minecraft/bin
    #   ln -s /var/prologin/minecraft/static/resources ~/.minecraft/resources
    #   ln -s /var/prologin/minecraft/static/servers.dat ~/.minecraft/servers.dat
    #   provide the minecraft/client/*.py tools for the user


COMPONENTS = [
    'bindcfg',
    'concours',
    'dhcpdcfg',
    'docs',
    'firewall',
    'hfs',
    'homepage',
    'irc_redmine_issues',
    'libprologin',
    'masternode',
    'mdb',
    'mdbdhcp',
    'mdbdns',
    'mdbsync',
    'minecraft',
    'netboot',
    'networkd',
    'nginxcfg',
    'paste',
    'presenced',
    'presencesync',
    'presencesync_cacheserver',
    'presencesync_firewall',
    'presencesync_usermap',
    'redmine',
    'resolved',
    'rfs',
    'set_hostname',
    'sshdcfg',
    'udb',
    'udbsync',
    'udbsync_django',
    'udbsync_passwd',
    'udbsync_redmine',
    'udbsync_rfs',
    'udbsync_rootssh',
    'workernode',
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
            system('groupadd -g %d %s' % (gid, gr))


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
            system(cmd)
        except KeyError:
            print('Creating user %r' % user)
            uid = data['uid']

            cmd = 'useradd -d /var/empty -M -N -u %d -g %s' % (uid, main_grp)
            if other_grps:
                cmd += ' -G %s' % ','.join(other_grps)
            cmd += ' ' + user
            system(cmd)


if __name__ == '__main__':
    os.umask(0)  # Trust our chmods.
    if len(sys.argv) == 1:
        print('usage: python3 install.py <component> [components...]')
        print('Components:')
        for name in sorted(COMPONENTS):
            print(' - %s' % name)
        sys.exit(1)

    if os.getuid() != 0:
        print('error: this script needs to be run as root')
        sys.exit(1)

    if not hasattr(sys, 'real_prefix'):
        print('error: this script needs to be run in a venv')
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

    if NEW_CFG:
        print('WARNING: Please review the newly installed config files:')
        for cfg in NEW_CFG:
            print(' - %s' % cfg)
