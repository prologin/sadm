import json
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext_lazy as _

from prologin.concours.oauth import models
from prologin.concours.oauth.utils import commit_oauth_response


class RefreshTokenMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if not self.get_response:
            self.get_response = lambda x: None

        # No behaviour during the final event
        if not settings.RUNNING_ONLINE or request.user.is_anonymous:
            return self.get_response(request)

        try:
            token_infos = models.OAuthToken.objects.get(user=request.user)
        except models.OAuthToken.DoesNotExist:
            logout(request)
            return self.get_response(request)

        res = requests.post(
            'http://{}/user/auth/refresh'.format(settings.HOST_WEBSITE_ROOT),
            json = {
                'refresh_token': token_infos.token,
                'client_id': settings.OAUTH_CLIENT_ID,
                'client_secret': settings.OAUTH_SECRET})
        data = res.json()

        user, created = User.objects.get_or_create(pk=data['user']['pk'],
            defaults={'username': data['user']['username']})
        login(request, user,
            backend='django.contrib.auth.backends.ModelBackend')
        commit_oauth_response(request, data)

        return self.get_response(request)

