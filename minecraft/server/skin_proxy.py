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

import os
import prologin.config
import tornado.ioloop
import tornado.web

SERVER_CFG = prologin.config.load('minecraft')


application = tornado.web.Application([
    (r'/MinecraftSkins/(.+?\.png)', tornado.Web.StaticFileHandler,
        {'path': SERVER_CFG['resources']['skin_dir']}),
    (r'/MinecraftCloaks/.+?\.png', tornado.Web.StaticFileHandler,
        {'path': os.path.join(SERVER_CFG['resources']['static_dir'], 'default_cape.png')}),
])


if __name__ == '__main__':
    import sys
    application.listen(int(sys.argv[1]))
    tornado.ioloop.IOLoop.instance().start()
