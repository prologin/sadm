from django.urls import include, path
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

import prologin.concours.stechec.urls
import prologin.concours.stechec.restapi.urls

from prologin.djangoconf import set_admin_title
set_admin_title(admin, "Concours")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(prologin.concours.stechec.restapi.urls)),
    path('', include(prologin.concours.stechec.urls)),
    path('', include('django_prometheus.urls')),
]

urlpatterns += staticfiles_urlpatterns()
