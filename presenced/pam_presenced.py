#! /var/prologin/venv/bin/python

"""Exit with status code 0 if $PAM_TYPE != "open_session" or if the $PAM_USER
exists and is allowed to log in. Exit with status code 1 otherwise.

In case the user happen to be handled by Prologin, hang until its HOME
directory is mounted.
"""

import os
import prologin.presenced
import sys

if os.environ.get('PAM_TYPE', None) != 'open_session':
    sys.exit(0)

login = os.environ['PAM_USER']

try:
    is_prologin_user = prologin.presenced.is_prologin_user(login)
except KeyError:
    # The user does not exist: should not happen, but forbid anyway.
    # TODO: notify sysadmins...
    sys.exit(1)

if not is_prologin_user:
    sys.exit(0)

if not prologin.presenced.connect().request_login(login):
    # Login is forbidden by presenced.
    sys.exit(1)

# TODO: request HOME directory migration and wait for it.

sys.exit(0)
