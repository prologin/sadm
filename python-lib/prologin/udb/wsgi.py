"""
WSGI config for prologin.udb project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

import prologin.config
from prologin.udb.views import UDBServer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prologin.udb.settings")
udb_cfg = prologin.config.load('udb-client-auth')

django_app = get_wsgi_application()

application = UDBServer(udb_cfg["shared_secret"])
application.add_wsgi_app(django_app)
