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
import prologin.config


# Validity time (in seconds) of a generated token.
TOKEN_TIMEOUT = 120


def generate_token(secret, message=None):
    """Generate a token given some `secret`."""
    timestamp = str(int(time.time()))
    return '{}:{}'.format(
        timestamp,
        get_hmac(secret, str(message) + timestamp),
    )


def check_token(token, secret, message=None):
    """Return if `token` is valid according to `secret` and current time."""

    config = prologin.config.load('timeauth')

    if not config['enabled']:
        return True

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

    # Check if the token is valid.
    return hmac.compare_digest(
        get_hmac(secret, str(message) + chunks[0]), chunks[1]
    )


def get_hmac(secret, message):
    """Return a HMAC of `message` for some `secret`."""
    return hmac.new(
        secret, message.encode('ascii'), digestmod=hashlib.sha256
    ).hexdigest()
