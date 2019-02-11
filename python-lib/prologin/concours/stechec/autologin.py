import json
import requests

from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin

class AutoLoginMiddleware(MiddlewareMixin):

    def process_request(self, request):
        res = requests.get(
            'http://localhost:8000/user/infos',
            cookies = {'sessionid': request.COOKIES['sessionid']})

        if res.text == 'unlogged':
            logout(request)
        else:
            user_infos = json.loads(res.text)

            try:
                user = User.objects.get(pk=user_infos['pk'])
                user.username = user_infos['username']
                user.first_name = user_infos['first_name']
                user.last_name = user_infos['last_name']
                user.is_superuser = user_infos['is_superuser']
                ser.is_staff = user_infos['is_staff']
            except:
                user = User.objects.create_user(
                    pk = user_infos['pk'],
                    username = user_infos['username'],
                    first_name = user_infos['first_name'],
                    last_name = user_infos['last_name'],
                    is_superuser = user_infos['is_superuser'],
                    is_staff = user_infos['is_staff'],
                    password=None,
                    email=None)

            user.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        if self.get_response:
            return self.get_response(request)

