#!/opt/prologin/venv/bin/python
# SPDX-License-Identifier: GPL-3.0-or-later

"""Sends periodic aliveness heartbeats to PresenceSync.

This is so we can free the username login lock after a machine crashes without
sending a proper logout signal.
"""

import logging
import subprocess
import time
from typing import Set

import prologin.config
import prologin.log
import prologin.presencesync.client
from prologin.presenced import current_hostname, is_prologin_user


def get_logged_on_prologin_users() -> Set[str]:
    """Returns the set of logged-on users that are handled by Prologin."""
    who = subprocess.check_output(['who', '-q'], encoding='utf-8')
    # Output of `$ who -q` looks like:
    #   foo bar qux
    #   # users=3
    return set(
        username
        for part in who.splitlines(keepends=False)[0].split()
        if (username := part.strip()) and is_prologin_user(username)
    )


def heartbeat_sender(interval_seconds: float):
    """Sends heartbeats to PresenceSync at a regular interval.

    :param interval_seconds: delay between two heartbeats. Of course, this
           should be less (with a comfy margin) than the presencesync timeout.
    """
    hostname = current_hostname()
    presencesync_client = prologin.presencesync.client.connect(publish=True)

    def send_heartbeat():
        usernames = get_logged_on_prologin_users()
        logging.debug("Heartbeat: logged-in users: %s", usernames)
        if len(usernames) == 0:
            pass
        elif len(usernames) == 1:
            presencesync_client.send_heartbeat(usernames.pop(), hostname)
        else:
            logging.error(
                "There are too many users logged in: %s", ", ".join(usernames)
            )

    while True:
        try:
            send_heartbeat()
            time.sleep(interval_seconds)
        except Exception:
            logging.exception("Error sending heartbeat to PresenceSYnc.")
            time.sleep(2)


if __name__ == "__main__":
    prologin.log.setup_logging('presenced')
    cfg = prologin.config.load('presencesync-sub')
    heartbeat_sender(interval_seconds=cfg['timeout'] / 2)
