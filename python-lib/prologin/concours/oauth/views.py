import requests
from urllib.parse import urlencode
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views.generic import RedirectView

from prologin.concours.oauth import models
from prologin.concours.oauth.utils import handle_oauth_response, gen_auth_state


class AutoLogin(RedirectView):

    def get_redirect_url(self):
        self.request.session['oauth_state'] = gen_auth_state()
        return '//{}/authorize?{}'.format(
            settings.OAUTH_ENDPOINT,
            urlencode({
                'client_id': settings.OAUTH_CLIENT_ID,
                'state': self.request.session['oauth_state']
            }))


class Callback(RedirectView):

    def get_redirect_url(self):
        return reverse('home')

    def get(self, request, *args, **kwargs):
        if 'oauth_state' not in request.session or request.GET['state'] != request.session['oauth_state']:
            return super().get(request, *args, **kwargs)

        res = requests.post(
            'http://{}/token'.format(settings.OAUTH_ENDPOINT),
            json = {
                'code': request.GET['code'],
                'client_id': settings.OAUTH_CLIENT_ID,
                'client_secret': settings.OAUTH_SECRET
            })
        data = res.json()
        handle_oauth_response(request, data)
        return super().get(request, *args, **kwargs)

