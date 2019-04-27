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

"""Utilities for Web API."""

import json
import prologin.timeauth
import requests
import urllib.parse


class Client:
    """Base client for sending authenticated requests."""

    def __init__(self, url):
        self.url = url

    def send_request(self, resource, secret, msg, url=None, method='post'):
        """Send an request that is authenticated using `secret` and that
        contains `msg` (a JSON data structure) to `resource`. Use client
        default URL if `url` is None. Return the request object.
        """
        try:
            data = json.dumps(msg)
        except TypeError:
            raise ValueError('non serializable argument type')

        full_url = urllib.parse.urljoin(url or self.url, resource)
        args = {
            'data': data,
            'hmac': prologin.timeauth.generate_token(secret, data),
        }
        if method == 'get':
            return requests.get(full_url, params=args)
        elif method == 'post':
            return requests.post(full_url, data=args)
        else:
            raise ValueError('Unsupported method: {}'.format(method))
