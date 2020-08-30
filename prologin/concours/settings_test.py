from pathlib import Path

from .settings_base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

SECRET_KEY = b'not-secret'

STECHEC_ROOT = Path("/tmp/sadm-test-stechec")
STECHEC_CONTEST = "prologinXXXX"
STECHEC_MASTER = "http://masternode/"
STECHEC_MASTER_SECRET = b"secret"
STECHEC_NPLAYERS = 2
STECHEC_USE_MAPS = True
STECHEC_MAP_VALIDATOR_SCRIPT = None
STECHEC_REPLAY = ""
STECHEC_REDMINE_ISSUE_LIST = "http://redmine/issues"
STECHEC_REDMINE_ISSUE_NEW = "http://redmine/issues/new"
STECHEC_FIGHT_ONLY_OWN_CHAMPIONS = False
