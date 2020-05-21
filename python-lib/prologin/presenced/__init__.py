import pwd
import socket


def current_hostname():
    """Returns current machine hostname, without .prolo suffix."""
    return socket.gethostname().rsplit('.', 1)[0]


def is_prologin_uid(uid):
    """Returns True if `uid` belongs to a user handled by Prologin."""
    return 10000 <= uid < 20000


def is_prologin_user(user):
    """Returns True if `user` (a username or an UID) is handled by Prologin.

    Raises KeyError if the user does not exist."""
    if isinstance(user, str):
        uid = pwd.getpwnam(user).pw_uid
    else:
        uid = pwd.getpwuid(user).pw_uid
    return is_prologin_uid(uid)
