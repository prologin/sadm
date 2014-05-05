"""
WSGI config for homepage project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "home.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paste.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from django.contrib.staticfiles.handlers import StaticFilesHandler
application = StaticFilesHandler(application)

# Copy of web.py, quick&dirty

import sys
import traceback


def exceptions_catched(func):
    """Decorator for function handlers: return a HTTP 500 error when an
    exception is raised.
    """
    def wrapper():
        try:
            return (200, 'OK') + func()
        except Exception:
            return (
                500, 'Error',
                {'Content-Type': 'text/html'},
                '<h1>Onoes, internal server error</h1>'
            )
    return wrapper

@exceptions_catched
def ping_handler():
    return { 'Content-Type': 'text/plain' }, "pong"

@exceptions_catched
def threads_handler():
    frames = sys._current_frames()
    text = ['%d threads found\n\n' % len(frames)]
    for i, frame in frames.items():
        s = 'Thread 0x%x:\n%s\n' % (i, ''.join(traceback.format_stack(frame)))
        text.append(s)
    return { 'Content-Type': 'text/plain' }, ''.join(text)

HANDLED_URLS = {
    '/__ping': ping_handler,
    '/__threads': threads_handler,
}

class WsgiApp:
    def __init__(self, app, app_name):
        self.app = app
        self.app_name = app_name

        # TODO(delroth): initialize logging

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'] in HANDLED_URLS:
            handler = HANDLED_URLS[environ['PATH_INFO']]
            return self.call_handler(environ, start_response, handler)
        return self.app(environ, start_response)

    def call_handler(self, environ, start_response, handler):
        status_code, reason, headers, content = handler()
        start_response(
            '{} {}'.format(status_code, reason),
            list(headers.items())
        )
        return [content.encode('utf-8')]


application = WsgiApp(application, 'paste')

from django.contrib.staticfiles.handlers import StaticFilesHandler
application = StaticFilesHandler(application)

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)
