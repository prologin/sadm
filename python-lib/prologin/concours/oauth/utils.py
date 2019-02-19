from django.contrib import messages
from django.contrib.auth import login, logout
from django.utils.crypto import get_random_string

from prologin.concours.oauth import models


# List of the attributes of User that are pulled from the main website
USER_SYNC_KEYS = ['username', 'first_name', 'last_name', 'is_superuser',
    'is_staff']


def gen_auth_state():
    return get_random_string(32)

def refresh_token(request, data):
    token_infos, created = models.OAuthToken.objects.get_or_create(
        user=request.user)
    token_infos.token = data['refresh_token']
    token_infos.expirancy = data['expires']
    token_infos.save()

def update_user(request, data):
    for key in USER_SYNC_KEYS:
        setattr(request.user, key, data['user'][key])

    request.user.save()

def commit_oauth_response(request, data):
    if 'error' in data:
        messages.add_message(request, messages.ERROR, data['error'])
        logout(request)
        return

    if request.user.pk != data['user']['pk']:
        logout(request)
        return

    refresh_token(request, data)
    update_user(request, data)

