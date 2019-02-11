import json
import requests

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin


class AutoLoginMiddleware(MiddlewareMixin):

    # List of the attributes of User that are pulled from the main website
    user_sync_keys = ['username', 'first_name', 'last_name', 'is_superuser',
        'is_staff']

    def process_request(self, request):
        if not self.get_response:
            self.get_response = lambda x: None

        if not settings.RUNNING_ONLINE:
            return self.get_response(request)

        res = requests.get(
            'http://{}/user/infos'.format(settings.HOST_WEBSITE_ROOT),
            cookies = {'sessionid': request.COOKIES['sessionid']})

        if res.text == 'unlogged':
            logout(request)
        else:
            user_infos = json.loads(res.text)

            try:
                user = User.objects.get(pk=user_infos['pk'])
            except User.DoesNotExist:
                user = User.objects.create_user(
                    pk=user_infos['pk'], username=user_infos['username'])

            for key in self.user_sync_keys:
                setattr(user, key, user_infos[key])

            user.save()

            if user.pk != request.user.pk:
                login(request, user,
                    backend='django.contrib.auth.backends.ModelBackend')

        return self.get_response(request)

