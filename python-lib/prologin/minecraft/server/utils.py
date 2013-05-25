#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Alexandre `Zopieux` Macabies <web@zopieux.com>
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


def login_from_host(presence_client, host):
    mapping = presence_client.get_list()
    for login, hostname in mapping.items():
        # FIXME: may need to get hostname from ip here
        if hostname == host:
            return login

    return None
