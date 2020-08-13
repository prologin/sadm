#! /opt/prologin/venv/bin/python
# SPDX-License-Identifier: GPL-3.0-or-later
"""PAM script to handle ``account``, ``open_session``, ``close_session`` hooks.

Intended integration inside ``/etc/pam.d/system-login``::

   account   requisite   pam_exec.so stdout /path/to/pam_prologin.py
   session   requisite   pam_exec.so stdout /path/to/pam_prologin.py

The ``account`` hook is responsible for checking the user is allowed to log-on
this particular machine by asking presencesync, and also does a mount/umount
cycle of the user home directory to ensure it will (most likely) succeed in
the next stage (open_session). This will possibly trigger an HFS move. We do
most of the blocking/long work inside ``account`` because it's the only stage
where we can send interactive messages to the PAM application (typically, a
greeter like lightdm). We cannot do that cleanly in ``open_session``.

Note: the ``account`` hook depends on a successful PAM ``auth`` stage,
typically through pam_passwd and udbsync_passwd.

The ``open_session`` hook mounts the user's home directory.

The ``close_session`` hook umounts the user's home directory.
"""

import json
import logging
import os
import os.path
import pathlib
import subprocess
import sys
import time

import prologin.hfs.client
import prologin.log
import prologin.presencesync.client
from prologin.presenced import is_prologin_user, current_hostname


class LoginError(Exception):
    pass


def format_exc_chain(exc):
    def get_recursive_cause(exc):
        if exc is None:
            return
        # In case the message is way too long, take only the first line.
        yield str(exc).splitlines(keepends=False)[0]
        yield from get_recursive_cause(getattr(exc, '__context__', None))

    return ': '.join(get_recursive_cause(exc))


def get_home_dir(username: str):
    return f'/home/{username}'


def get_block_device(username):
    return '/dev/nbd0'


def invoke_redirect_std(cmd, **kwargs):
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, **kwargs)


def send(msg: str, error: bool = False):
    sys.stderr.write(json.dumps({"message": msg, "isError": error}) + "\n")
    sys.stderr.flush()


def pause():
    time.sleep(1)


def check_presencesync_authorized(username: str, hostname: str):
    # Request the login to presencesync.
    presencesync_client = prologin.presencesync.client.connect(publish=True)
    failure_reason = presencesync_client.request_login(username, hostname)
    if failure_reason is not None:
        # Login is forbidden by presencesync, typically because already
        # logged-on somewhere else.
        raise LoginError(f"Login forbidden: {failure_reason}")


def get_hfs_host_port(username: str, hostname: str):
    """Requests user NBD (can involve a migration) and waits for it."""
    return prologin.hfs.client.connect().get_hfs(username, hostname)


def mount_home(username: str, host: str, port: int):
    """Mounts block device for ``username`` using HFS ``host:port``."""
    home_dir = get_home_dir(username)

    # Already mounted? Nothing to do.
    if os.path.ismount(home_dir):
        return

    # Create the HOME mount point if needed. There is no need to fix
    # permissions: this is only a mount point.
    pathlib.Path(home_dir).mkdir(exist_ok=True)

    # Get a block device for the HOME mount point and mount it.
    #
    # Containers used for testing do not have the netlink nbd family available
    # (see genl-ctrl-list(8)), therefore fallback to using ioctl with the
    # -nonetlink option. Exercise for the reader: figure how to enable the ndb
    # netlink family in a systemd-nspawn container.
    #
    # TODO: experiment with '-block-size' values and compare performance
    block_device = get_block_device(username)
    invoke_redirect_std(
        [
            '/usr/sbin/nbd-client',
            '-nonetlink',
            '-name',
            username,
            host,
            str(port),
            block_device,
        ]
    )
    invoke_redirect_std(['/bin/mount', block_device, home_dir])


def umount_home(username: str):
    """Unmounts block device for ``username``."""
    home_dir = get_home_dir(username)

    if os.path.ismount(home_dir):
        invoke_redirect_std(['/bin/umount', '-R', home_dir])

    # Stop the nbd client.
    # Due to a bug somewhere between nbd-client and the kernel, detaching with
    # -nonetlink fails with: 'Invalid nbd device target /dev/nbd0'.
    block_device = get_block_device(username)
    try:
        invoke_redirect_std(['/usr/sbin/nbd-client', '-d', block_device])
    except subprocess.CalledProcessError:
        # Here's the workaround: only try without -nonetlink if the above
        # command fails.
        invoke_redirect_std(
            ['/usr/sbin/nbd-client', '-d', '-nonetlink', block_device]
        )


def handle_account(username: str):
    """
    Checks the user is allowed to log on and does a dry-run mount/umount cycle.
    """
    # Exit early if user is already logged in
    if os.path.ismount(get_home_dir(username)):
        return

    hostname = current_hostname()
    send("Checking user…")
    check_presencesync_authorized(username, hostname)

    send("Requesting home…")
    try:
        host, port = get_hfs_host_port(username, hostname)
    except Exception:
        raise LoginError("While retrieving HFS")

    send("Test-mounting home…")
    try:
        mount_home(username, host, port)
    except Exception:
        raise LoginError("While test-mounting home")

    send("Test-umounting home…")
    try:
        umount_home(username)
    except Exception:
        raise LoginError("While test-umounting home")


def handle_open_session(username: str):
    """Same as :func:`handle_account`, but doesn't do the final umount.

    In-situ, we expect this function to fail less often than
    :func:`handle_account`."""
    # Exit early if user is already logged in
    if os.path.ismount(get_home_dir(username)):
        return

    hostname = current_hostname()
    # This will most likely succeed since we already did it moments ago.
    check_presencesync_authorized(username, hostname)

    try:
        # This will most likely be cached from before, and therefore instant.
        host, port = get_hfs_host_port(username, hostname)
    except Exception:
        raise LoginError("While retrieving HFS")

    try:
        # Same here, this is expected to work.
        mount_home(username, host, port)
    except Exception:
        raise LoginError("While mounting home")


def handle_close_session(username: str):
    """Cleans up user session by killing all processes and umounting."""
    # Make sure the user has nothing else running.
    try:
        invoke_redirect_std(['/usr/bin/pkill', '-9', '-u', username])
    except subprocess.CalledProcessError as err:
        # "No processes matched" errors are fine.
        if err.returncode != 1:
            logging.exception("Error pkill'ing user '%s' processes", username)

    # Umount /home/user. I don't know why the sleep is necessary.
    time.sleep(2)
    umount_home(username)


def main():
    # We use stderr for communication with PAM. Don't write on it.
    prologin.log.setup_logging('pam_prologin', local=False)

    pam_type = os.environ['PAM_TYPE']
    pam_service = os.environ['PAM_SERVICE']
    pam_user = os.environ['PAM_USER']

    # PAM is a modular system and anyone can invoke it for other purposes than
    # login users. systemd-user for instance asks PAM about the user account
    # during its session pam_systemd hook. To prevent running expensive stuff
    # twice, blacklist such undesirable uses. An alternative would be to
    # whitelist all greeters, but that's higher maintenance.
    blacklisted_pam_services = {"systemd-user"}
    if pam_service in blacklisted_pam_services:
        return 0

    # System users not controlled by udb are unrestricted. Exit early.
    if not is_prologin_user(pam_user):
        return 0

    handler = {
        "account": handle_account,
        "open_session": handle_open_session,
        "close_session": handle_close_session,
    }.get(pam_type)

    if not handler:
        # Pass-trough anything we don't explicitly handle.
        return 0

    logging.debug(
        "pam_prologin invoked for type=%s, service=%s, user=%s",
        pam_type,
        pam_service,
        pam_user,
    )

    try:
        handler(pam_user)
        logging.info("Execution of handler for PAM %s succeeded", pam_type)
        return 0
    except Exception as exc:
        logging.exception("Error executing handler for PAM %s", pam_type)
        send(format_exc_chain(exc), True)
        pause()
        return 1


if __name__ == '__main__':
    sys.exit(main())
