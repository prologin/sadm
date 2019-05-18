#! /opt/prologin/venv/bin/python
"""PAM script to handle {open,close}_session events.

Exit with status code 0 if used for another event.  Exit with status code 0 if
the $PAM_USER exists and is allowed to log in. Exit with status code 1
otherwise.

For open_session, in case the user login is accepted and is handled by
Prologin, try to mount its HOME directory and hang until it is done. For
close_session, try to unmount it.
"""

import logging
import os
import os.path
import socket
import subprocess
import sys
import time

import prologin.hfs.client
import prologin.log
import prologin.presenced.client
import prologin.xhack

sys.stderr = open('/tmp/pam_log', 'a')
prologin.log.setup_logging('pam_presenced')


def get_home_dir(login):
    return '/home/{}'.format(login)


def get_block_device(login):
    return '/dev/nbd0'


def fail(reason):
    print(reason, file=sys.stderr)
    logging.error(reason)
    prologin.xhack.run(['/usr/bin/zenity', '--error', '--text', reason])
    sys.exit(1)


PAM_TYPE = os.environ['PAM_TYPE']
PAM_SERVICE = os.environ['PAM_SERVICE']
login = os.environ['PAM_USER']

try:
    is_prologin_user = prologin.presenced.client.is_prologin_user(login)
except KeyError:
    # The login/password was accepted by pam_unix.so, but user does not exist:
    # should not happen, but forbid anyway.  TODO: notify sysadmins...
    fail('No such user')

if PAM_TYPE == 'open_session' and not os.path.ismount(get_home_dir(login)):
    # Not-prologin users are not resticted at all.
    if not is_prologin_user:
        sys.exit(0)

    # Prologin users must use a display manager (not a TTY, nor screen).
    if PAM_SERVICE not in ('gdm', 'kde', 'slim', 'xdm', 'sddm'):
        logging.warning(
            'User %s is not logging in with a graphical display manager',
            login)

    # Request the login to Presenced and PresenceSync.
    failure_reason = prologin.presenced.client.connect().request_login(login)
    if failure_reason is not None:
        # Login is forbidden by presenced.
        fail('Login forbidden: {}'.format(failure_reason))

    # Request HOME directory migration and wait for it.
    hfs = prologin.hfs.client.connect()
    try:
        hostname = socket.gethostname()
        if hostname.endswith('.prolo'):
            hostname = hostname[:-len('.prolo')]
        else:
            logging.warning('Hostname does not end with .prolo: %s', hostname)
        host, port = hfs.get_hfs(login, hostname)
    except RuntimeError as e:
        fail(str(e))

    block_device = get_block_device(login)
    home_dir = get_home_dir(login)

    # Create the HOME mount point if needed.
    if not os.path.exists(home_dir):
        # There is no need to fix permissions: this is only a mount point.
        os.mkdir(home_dir)

    # Get a block device for the HOME mount point and mount it.
    #
    # Containers used for testing do not have the netlink nbd family available
    # (see genl-ctrl-list(8)), therefore fallback to using ioctl with the
    # -nonetlink option. Exercise for the reader: figure how to enable the ndb
    # netlink family in a systemd-nspawn container.
    #
    # TODO: experiment with '-block-size' values and compare performance
    if subprocess.check_call([
            '/usr/sbin/nbd-client', '-nonetlink', '-name', login, host,
            str(port), block_device
    ],
                             stdout=sys.stderr,
                             stderr=sys.stderr):
        fail('Cannot get the home directory block device')
    if subprocess.check_call(['/bin/mount', block_device, home_dir],
                             stdout=sys.stderr,
                             stderr=sys.stderr):
        fail('Cannot mount the home directory')

    sys.exit(0)

elif PAM_TYPE == 'close_session':
    if is_prologin_user:
        # Make sure the user has nothing else running
        try:
            subprocess.check_call(['/usr/bin/pkill', '-9', '-u', login],
                                  stdout=sys.stderr,
                                  stderr=sys.stderr)
        except subprocess.CalledProcessError as e:
            if e.returncode != 1:  # "No processes matched" we don't care
                raise e

        # Unmount /home/user
        time.sleep(2)
        subprocess.check_call(
            ['/bin/umount', '-R', get_home_dir(login)],
            stdout=sys.stderr,
            stderr=sys.stderr)

        # And finally stop the nbd client
        block_device = get_block_device(login)

        # due to a bug somewhere between nbd-client and the kernel, detaching
        # with -nonetlink fails with: Invalid nbd device target /dev/nbd0
        nbdstop = subprocess.run(
                ['/usr/sbin/nbd-client', '-d', block_device],
                stdout=sys.stderr,
                stderr=sys.stderr)
        # here's the workaround : only try without -nonetlink if the above
        # command fails
        if nbdstop.returncode != 0:
            subprocess.check_call(
                    ['/usr/sbin/nbd-client', '-d', '-nonetlink', block_device],
                    stdout=sys.stderr,
                    stderr=sys.stderr)
    sys.exit(0)

else:
    sys.exit(0)
