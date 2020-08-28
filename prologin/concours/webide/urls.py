from django.urls import path, include
from . import api

app_name = 'webide'

urlpatterns = [
        path('api/', include(api.router.urls)),
]
