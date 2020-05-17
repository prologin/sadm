"""
WSGI config for prologin.udb project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prologin.udb.settings")

wsgi_app = get_wsgi_application()

from prologin.udb.views import UDBServer

application = UDBServer()
application.add_wsgi_app(wsgi_app)
