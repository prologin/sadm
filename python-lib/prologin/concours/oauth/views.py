import requests

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views.generic import RedirectView

from prologin.concours.oauth import models
from prologin.concours.oauth.utils import commit_oauth_response, gen_auth_state


class AutoLogin(RedirectView):

    def get_redirect_url(self):
        self.request.session['oauth_state'] = gen_auth_state()
        return '//{}/user/auth/authorize?client_id={}&state={}'.format(
            settings.HOST_WEBSITE_ROOT, settings.OAUTH_CLIENT_ID,
            self.request.session['oauth_state'])


class Callback(RedirectView):

    def get_redirect_url(self):
        return reverse('home')

    def get(self, request, *args, **kwargs):
        res = requests.post(
            'http://{}/user/auth/token'.format(settings.HOST_WEBSITE_ROOT),
            json = {
                'code': request.GET['code'],
                'client_id': settings.OAUTH_CLIENT_ID,
                'client_secret': settings.OAUTH_SECRET})

        if 'oauth_state' not in request.session or request.GET['state'] != request.session['oauth_state']:
            return super().get(request, *args, **kwargs)

        data = res.json()
        user, created = User.objects.get_or_create(pk=data['user']['pk'],
            defaults={'username': data['user']['username']})
        login(request, user,
            backend='django.contrib.auth.backends.ModelBackend')

        commit_oauth_response(request, data)
        return super().get(request, *args, **kwargs)

