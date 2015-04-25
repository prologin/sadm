from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.middleware import RemoteUserMiddleware


class SSOMiddleware(RemoteUserMiddleware):
    """
    Custom RemoteUserMiddleware. As nginx acts as a proxy to gunicorn, we can't
    pass environment variables, we have to use HTTP headers, hence
    *HTTP*_REMOTE_USER.
    """
    header = "HTTP_REMOTE_USER"


class SSOUserBackend(RemoteUserBackend):
    """
    Custom RemoteUserBackend. Prevent the creation of SSO-provided users if
    they're not in local database.
    """
    create_unknown_user = False
