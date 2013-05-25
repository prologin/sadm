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

import Image
import io
import json
import logging
import os
import prologin.config
import prologin.log
import prologin.presencesync
import tornado.ioloop
import tornado.web
from utils import login_from_host

SERVER_CFG = prologin.config.load('minecraft')
PRESENCED_CFG = prologin.config.load('presenced-client')

SKIN_SIZE = (64, 32)

presence_client = prologin.presencesync.connect()


class GetLoginHandler(tornado.web.RequestHandler):
    def get(self):
        login = login_from_host(presence_client, self.request.remote_ip)

        if login is not None:
            logging.debug("Found mapping `%s` -> `%s`",
                self.request.remote_ip, login)
            self.finish(login.encode('utf8'))
        else:
            logging.warn("Unable to find login from host `%s`",
                self.request.remote_ip)
            self.set_status(404)
            self.finish("User not found")


class SkinUploadHandler(tornado.web.RequestHandler):
    def _send_status(self, ok, msg):
        self.set_status(200 if ok else 400)
        self.content_type = 'application/json'
        self.finish(json.dumps({'ok': ok, 'msg': msg}))

    def put(self):
        login = login_from_host(presence_client, self.request.remote_ip)
        if login is None:
            self._send_status(False, "Utilisateur inconnu")
            return

        fileinfo = self.request.files['skin'][0]
        buff = io.BytesIO(fileinfo['body'])
        try:
            im = Image.open(buff)
            im.verify()
        except Exception:
            self._send_status(False, "Format de fichier invalide")
            return

        if im.size != SKIN_SIZE:
            self._send_status(False, "L'image doit être de dimensions %dx%d" % SKIN_SIZE)
            return

        with open(os.path.join(SERVER_CFG['resources']['skin_dir'], '%s.png' % login), 'wb') as f:
            f.write(fileinfo['body'])

        self._send_status(True, "")

    def delete(self):
        login = login_from_host(self.request.remote_ip)
        if login is None:
            self._send_status(False, "Utilisateur inconnu")
            return

        try:
            os.remove(os.path.join(SERVER_CFG['resources']['skin_dir'], '%s.png' % login))
            self._send_status(True, "")
        except (IOError, OSError):
            self._send_status(False,
                "Impossible de supprimer le skin (il n'existait sûrement pas)")


application = tornado.web.Application([
    (r'/mylogin', GetLoginHandler),
    (r'/skin', SkinUploadHandler),
])


if __name__ == '__main__':
    prologin.log.setup_logging('minecraft-webserver')

    import sys
    application.listen(int(sys.argv[1]))
    tornado.ioloop.IOLoop.instance().start()
