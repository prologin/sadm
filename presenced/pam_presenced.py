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

# TODO: request HOME directory migration and wait for it.

sys.exit(0)
