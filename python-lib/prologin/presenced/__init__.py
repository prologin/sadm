import pwd
import socket
from typing import Union


def current_hostname() -> str:
    """Returns current machine hostname, without .prolo suffix."""
    return socket.gethostname().rsplit('.', 1)[0]


def is_prologin_uid(uid: int) -> bool:
    """Returns True if `uid` belongs to a user handled by Prologin."""
    return 10000 <= uid < 20000


def is_prologin_user(user: Union[str, int]) -> bool:
    """Returns True if ``user`` (a username or a UID) is handled by Prologin.

    Returns False if the user does not exist."""
    try:
        if isinstance(user, str):
            uid = pwd.getpwnam(user).pw_uid
        else:
            uid = pwd.getpwuid(user).pw_uid
    except KeyError:
        return False
    return is_prologin_uid(uid)
