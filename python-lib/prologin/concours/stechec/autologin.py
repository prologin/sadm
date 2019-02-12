import json
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext_lazy as _


class AutoLoginMiddleware(MiddlewareMixin):

    # List of the attributes of User that are pulled from the main website
    user_sync_keys = ['username', 'first_name', 'last_name', 'is_superuser',
        'is_staff']

    def process_request(self, request):
        if not self.get_response:
            self.get_response = lambda x: None

        # No behaviour during the final event
        if not settings.RUNNING_ONLINE:
            return self.get_response(request)

        # Catch user informations from main website's API
        if 'sessionid' not in request.COOKIES:
            # this user may have never opened the main website
            data = {'logged': False}
        else:
            try:
                res = requests.get(
                    'http://{}/user/infos'.format(settings.HOST_WEBSITE_ROOT),
                    cookies = {'sessionid': request.COOKIES['sessionid']})
                data = res.json()
            except json.JSONDecodeError:
                messages.add_message(request, messages.ERROR,
                    _('Error while syncing login informations with the main website'))
                data = {'logged': False}

        if not data['logged']:
            logout(request)
        else:
            user_infos = data['user_infos']

            # Retrieve user corresponding to user logged on main website, or
            # create a new user
            try:
                user = User.objects.get(pk=user_infos['pk'])
            except User.DoesNotExist:
                user = User.objects.create_user(
                    pk=user_infos['pk'], username=user_infos['username'])

            # Update local database with fields received from main website's
            for key in self.user_sync_keys:
                setattr(user, key, user_infos[key])

            user.save()

            # Update the user that is logged in
            if user.pk != request.user.pk:
                login(request, user,
                    backend='django.contrib.auth.backends.ModelBackend')

        return self.get_response(request)

