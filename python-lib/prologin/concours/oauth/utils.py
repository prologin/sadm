from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
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

def handle_oauth_response(request, data):
    if 'error' in data:
        messages.add_message(request, messages.ERROR,
            'Erreur d\'authentification:' + data['error'])
        logout(request)
        return False

    user, created = User.objects.get_or_create(pk=data['user']['pk'],
            defaults={field: data['user'][field] for field in USER_SYNC_KEYS})
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    if not created:
        update_user(request, data)

    refresh_token(request, data)
    return True

