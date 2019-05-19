from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

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

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
