from pathlib import Path

from .settings_base import *

from prologin.djangoconf import use_profile_config

cfg = use_profile_config('concours')

if cfg['website'].get('static_path'):
    # Overwrite local static files with static_path assets
    STATICFILES_DIRS += [cfg['website']['static_path']]

STECHEC_ROOT = Path(cfg["contest"]["directory"])
STECHEC_CONTEST = cfg["contest"]["game"]
STECHEC_MASTER = cfg["master"]["url"]
STECHEC_MASTER_SECRET = cfg["master"]["shared_secret"].encode('utf-8')
STECHEC_NPLAYERS = cfg["contest"]["nb_players"]
STECHEC_USE_MAPS = cfg["contest"]["use_maps"]
STECHEC_MAP_VALIDATOR_SCRIPT = cfg["contest"]["map_validator_script"]
STECHEC_REPLAY = cfg["website"]["replay"]
STECHEC_REDMINE_ISSUE_LIST = cfg["redmine_urls"]["issue_list"]
STECHEC_REDMINE_ISSUE_NEW = cfg["redmine_urls"]["issue_new"]
STECHEC_FIGHT_ONLY_OWN_CHAMPIONS = cfg["contest"]["fight_only_own_champions"]


# online mode configuration

if cfg['online_mode'].get('enabled'):
    CONCOURS_ONLINE_MODE = True
    OAUTH_ENDPOINT += cfg['online_mode']['oauth_endpoint']
    OAUTH_CLIENT_ID += cfg['online_mode']['oauth_client_id']
    OAUTH_SECRET += cfg['online_mode']['oauth_secret']

    INSTALLED_APPS.append('proloauth_client')

    AUTHENTICATION_BACKENDS.remove('prologin.sso.django.SSOUserBackend')
    MIDDLEWARE.remove('prologin.sso.django.SSOMiddleware')
    MIDDLEWARE.insert(
        MIDDLEWARE.index('django.middleware.csrf.CsrfViewMiddleware'),
        'proloauth_client.middleware.RefreshTokenMiddleware',
    )
