"""
WSGI config for prologin.mdb project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application
from prologin.mdb.views import MDBServer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prologin.mdb.settings")

django_app = get_wsgi_application()

application = MDBServer()
application.add_wsgi_app(django_app)
