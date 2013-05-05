#! /var/prologin/venv/bin/python

"""Exit with status code 0 if $PAM_TYPE != "open_session" or if the $PAM_USER
exists and is allowed to log in. Exit with status code 1 otherwise.

In case the user happen to be handled by Prologin, hang until its HOME
directory is mounted.
"""

import os
import prologin.hfs
import prologin.presenced
import socket
import subprocess
import sys

def get_home_dir(login):
    return '/home/{}'.format(login)

def get_block_device(login):
    return '/dev/ndb{}'.format(login)

if os.environ.get('PAM_TYPE', None) == 'close_session':
    login = os.environ['PAM_USER']
    subprocess.call(['umount', get_home_dir(login)])
    subprocess.call(['ndb-client', '-d', get_block_device(login)])
    sys.exit(0)

elif os.environ.get('PAM_TYPE', None) != 'open_session':
    sys.exit(0)

def fail(reason):
    # TODO: be sure the user can see the reason.
    print(reason, file=sys.stderr)
    sys.exit(1)

login = os.environ['PAM_USER']

try:
    is_prologin_user = prologin.presenced.is_prologin_user(login)
except KeyError:
    # The user does not exist: should not happen, but forbid anyway.
    # TODO: notify sysadmins...
    fail('No such user')

if not is_prologin_user:
    sys.exit(0)

failure_reason = prologin.presenced.connect().request_login(login)
if failure_reason:
    # Login is forbidden by presenced.
    fail('Login forbidden: {}'.format(failure_reason))

# Request HOME directory migration and wait for it.
hfs = prologin.hfs.connect()
try:
    host, port = hfs.get_hfs(login, socket.gethostname())
except RuntimeError as e:
    fail(str(e))

# Get a block device for the HOME mount point.
block_device = get_block_device(login)
home_dir = get_home_dir(login)
if subprocess.call(['nbd-client', '{}:{}', block_device]):
    fail('Cannot get the home directory block device')
if subprocess.call(['mount', block_device, home_dir]):
    fail('Cannot mount the home directory')

sys.exit(0)
