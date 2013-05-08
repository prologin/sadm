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


import logging
import os
import prologin.config
import prologin.log
import requests
from lxml import etree
from io import BytesIO

RES_CFG = prologin.config.load('minecraft')


def download_resources():
    root = os.path.join(RES_CFG['resources']['static_dir'], 'resources')
    page = etree.parse(BytesIO(
        requests.get(RES_CFG['resources']['media_url']).content))

    for content in page.findall('Contents'):
        path = content.find('Key').text
        size = int(content.find('Size').text)
        if size == 0:
            os.makedirs(os.path.join(root, path), mode=0o755, exist_ok=True)
        else:
            with open(os.path.join(root, path), 'wb') as f:
                f.write(requests.get(
                    RES_CFG['resources']['media_url'] + path).content)
            logging.debug("Downloaded resource: %s (%d bytes)", path, size)


if __name__ == '__main__':
    download_resources()
