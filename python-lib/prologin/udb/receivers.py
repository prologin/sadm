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
import atexit
import logging
import prologin.log
import prologin.udbsync.client
import queue
import threading

from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete
from prologin.udb.models import User

prologin.log.setup_logging('udb')


class UpdateSenderTask(threading.Thread):
    STOP_GUARD = object()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updates_queue = queue.Queue()
        self.daemon = True
        self.start()

    def send(self, update):
        self.updates_queue.put(update)

    def run(self):
        self.running = True
        while self.running:
            updates = [self.updates_queue.get()]

            try:
                while len(updates) < 10:
                    updates.append(self.updates_queue.get(timeout=0.1))
            except queue.Empty:
                pass

            if any(update is self.STOP_GUARD for update in updates):
                self.running = False
                updates = list(filter(lambda x: x is not self.STOP_GUARD, updates))

            try:
                cl = prologin.udbsync.client.connect(pub=True)
                cl.send_updates(updates)
            except Exception:
                logging.exception("unable to send updates to udbsync")

    def stop(self):
        self.updates_queue.put(self.STOP_GUARD)

    def join(self):
        self.stop()
        super().join()

_update_sender = UpdateSenderTask()
atexit.register(_update_sender.join)

@receiver(post_save)
def post_save_handler(sender, instance, created, *args, **kwargs):
    if sender is not User:
        return
    _update_sender.send({ "type": "update", "data": instance.to_dict() })

@receiver(pre_delete)
def pre_delete_handler(sender, instance, *args, **kwargs):
    if sender is not User:
        return
    _update_sender.send({ "type": "delete", "data": instance.to_dict() })
