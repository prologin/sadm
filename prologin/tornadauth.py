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

"""Utilities for authentication in Tornado servers."""

import logging
import prologin.timeauth


def signature_checked(secret_name, check_msg=False):
    """Return a decorator for Tornado requests handlers' methods.

    The decorator wraps a given method handler so that the signature of
    requests are checked before calling the handler itself. If checking fails,
    log the failure and return a HTTP 403 error. The shared secret used for
    checking is the `secret_name` attribute of the Tornado application
    associated to the handler. Include message checking if asked to.
    """

    def decorator(func):
        def method_wrapper(self):
            msg = self.get_argument('data') if check_msg else None
            secret = getattr(self.application, secret_name)
            if not prologin.timeauth.check_token(
                self.get_argument('hmac'), secret, msg
            ):
                logging.error('INVALID TOKEN!')
                self.set_status(403, 'Invalid token')
                self.write('Invalid token')
            else:
                return func(self, self.get_argument('data'))

        return method_wrapper

    return decorator
