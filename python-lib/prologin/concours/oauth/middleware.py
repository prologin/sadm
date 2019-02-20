import requests

from django.conf import settings
from django.contrib.auth import logout
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin

from prologin.concours.oauth import models
from prologin.concours.oauth.utils import handle_oauth_response


class RefreshTokenMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if request.user.is_anonymous:
            return

        try:
            token_infos = models.OAuthToken.objects.get(user=request.user)
        except models.OAuthToken.DoesNotExist:
            logout(request)
            return

        try:
            res = requests.post(
                '{}/refresh'.format(settings.OAUTH_ENDPOINT),
                json = {
                    'refresh_token': token_infos.token,
                    'client_id': settings.OAUTH_CLIENT_ID,
                    'client_secret': settings.OAUTH_SECRET})
            data = res.json()
        except:
            return HttpResponseRedirect(reverse('autologin'))

        if not handle_oauth_response(request, data):
            return HttpResponseRedirect(reverse('autologin'))

