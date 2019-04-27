from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.middleware import RemoteUserMiddleware


class SSOMiddleware(RemoteUserMiddleware):
    """
    Custom RemoteUserMiddleware. As nginx acts as a proxy to gunicorn, we can't
    pass environment variables, we have to use HTTP headers, hence
    *HTTP*_REMOTE_USER.
    """
    header = "HTTP_X_SSO_USER"


class SSOUserBackend(RemoteUserBackend):
    """
    Custom RemoteUserBackend. Prevent the creation of SSO-provided users if
    they're not in local database.

    It is the role of Django udbsync client to populate the local user database.
    """
    create_unknown_user = False
