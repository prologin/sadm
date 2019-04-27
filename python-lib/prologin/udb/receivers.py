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
import logging
import prologin.log
import prologin.udbsync.client

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from prologin.synchronisation import UpdateSenderTask
from prologin.udb.models import User

prologin.log.setup_logging('udb')

def _udb_send_updates(updates):
    try:
        conn = prologin.udbsync.client.connect(pub=True)
        conn.send_updates(updates)
    except Exception:
        logging.exception("Error while sending udb updates")

_update_sender = UpdateSenderTask(_udb_send_updates)

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
