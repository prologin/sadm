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

"""Tiny utilities to authenticate connections using a pre-shared secret and
time synchronisation between endpoints.
"""

import hashlib
import hmac
import time


# Validity time (in seconds) of a generated token.
TOKEN_TIMEOUT = 10


def generate_token(secret):
    """Generate a token given some `secret`."""
    timestamp = str(int(time.time()))
    timestamp_hmac = get_hmac(secret, timestamp)
    return '{}:{}'.format(timestamp, timestamp_hmac)


def check_token(secret, token):
    """Return if `token` is valid according to `secret` and current time."""

    if token is None:
        return False

    # Reject badly formatted tokens.
    chunks = token.split(':')
    if len(chunks) != 2:
        return False
    try:
        timestamp = int(chunks[0])
    except ValueError:
        return False

    # Reject outdated tokens.
    if time.time() - timestamp > TOKEN_TIMEOUT:
        return False

    # Reject invalid tokens.
    timestamp_hmac = get_hmac(secret, chunks[0])
    if timestamp_hmac != chunks[1]:
        return False

    # What remains should be valid.
    return True


def get_hmac(secret, timestamp):
    """Return a HMAC of `timestamp` for some `secret`."""
    return hmac.new(
        secret,
        timestamp.encode('ascii'),
        digestmod=hashlib.sha256
    ).hexdigest()
