import json
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext_lazy as _

import prologin.concours.stechec.models as models


class AutoLoginMiddleware(MiddlewareMixin):

    # List of the attributes of User that are pulled from the main website
    user_sync_keys = ['username', 'first_name', 'last_name', 'is_superuser',
        'is_staff']

    def process_request(self, request):
        if not self.get_response:
            self.get_response = lambda x: None

        # No behaviour during the final event
        if not settings.RUNNING_ONLINE or request.user.is_anonymous:
            return self.get_response(request)

        token_infos, created = models.OAuthToken.objects.get_or_create(
            user=request.user)

        if token_infos.token is None:
            logout(request)
            return self.get_response(request)

        res = requests.post(
            'http://{}/user/auth/refresh'.format(settings.HOST_WEBSITE_ROOT),
            json = {
                'refresh_token': token_infos.token,
                'client_id': settings.OAUTH_CLIENT_ID,
                'client_secret': settings.OAUTH_SECRET})

        data = res.json()
        print(data)

        if 'error' in data:
            messages.add_message(request, messages.ERROR, data['error'])
            logout(request)
            return self.get_response(request)

        user, created = User.objects.get_or_create(pk=data['user']['pk'],
            defaults={'username': data['user']['username']})
        user_sync_keys = ['username', 'first_name', 'last_name',
            'is_superuser', 'is_staff']

        for key in user_sync_keys:
            setattr(user, key, data['user'][key])

        token_infos.token = data['refresh_token']
        token_infos.expirancy = data['expires']
        token_infos.save()

        login(request, user,
            backend='django.contrib.auth.backends.ModelBackend')

        return self.get_response(request)

