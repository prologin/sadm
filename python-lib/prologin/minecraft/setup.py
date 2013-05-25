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
import shutil
from lxml import etree
from io import BytesIO
from nbt import *

RES_CFG = prologin.config.load('minecraft')
AWS_NAMESPACE = '{http://s3.amazonaws.com/doc/2006-03-01/}'


def download_resources():
    root = os.path.join(RES_CFG['resources']['static_dir'], 'resources')
    page = etree.parse(BytesIO(
        requests.get(RES_CFG['resources']['media_url']).content))

    for content in page.findall('%sContents' % AWS_NAMESPACE):
        path = content.find('%sKey' % AWS_NAMESPACE).text
        size = int(content.find('%sSize' % AWS_NAMESPACE).text)
        if size == 0:
            os.makedirs(os.path.join(root, path), mode=0o755, exist_ok=True)
        else:
            with open(os.path.join(root, path), 'wb') as f:
                f.write(requests.get(
                    RES_CFG['resources']['media_url'] + path).content)
            os.chmod(f.name, 0o644)
            shutil.chown(f.name, 'minecraft', 'minecraft')
            logging.debug("Downloaded resource: %s (%d bytes)", path, size)

    logging.info("Successfully downloaded all Minecraft resources")


def write_servers_dat():
    nbtfile = NBTFile()
    nbtfile.name = ''
    root = TAG_List(type=TAG_Compound, name='servers')
    prolocraft = TAG_Compound()
    prolocraft.tags.append(TAG_Byte(name='hideAddress', value=0))
    prolocraft.tags.append(TAG_String(name='name', value=RES_CFG['server']['human_name']))
    prolocraft.tags.append(TAG_String(name='ip', value=RES_CFG['server']['host']))
    root.tags.append(prolocraft)
    nbtfile.tags.append(root)

    with open(os.path.join(RES_CFG['resources']['static_dir'], 'servers.dat'), 'wb') as f:
        nbtfile.write_file(buffer=f)
        os.chmod(f.name, 0o644)
        shutil.chown(f.name, 'minecraft', 'minecraft')
        logging.info("Wrote %s" % f.name)


if __name__ == '__main__':
    prologin.log.setup_logging('minecraft-setup')
    write_servers_dat()
    download_resources()
