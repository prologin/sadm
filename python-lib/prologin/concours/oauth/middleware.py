import json
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext_lazy as _

from prologin.concours.oauth import models
from prologin.concours.oauth.utils import handle_oauth_response


class RefreshTokenMiddleware(MiddlewareMixin):

    def process_request(self, request):
        # No behaviour during the final event
        if not settings.RUNNING_ONLINE or request.user.is_anonymous:
            return

        try:
            token_infos = models.OAuthToken.objects.get(user=request.user)
        except models.OAuthToken.DoesNotExist:
            logout(request)
            return

        res = requests.post(
            'http://{}/user/auth/refresh'.format(settings.OAUTH_ENDPOINT),
            json = {
                'refresh_token': token_infos.token,
                'client_id': settings.OAUTH_CLIENT_ID,
                'client_secret': settings.OAUTH_SECRET})
        data = res.json()

        if not handle_oauth_response(request, data):
            return HttpResponseRedirect(reverse('autologin'))

