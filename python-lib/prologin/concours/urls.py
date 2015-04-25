from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

import prologin.concours.stechec.urls

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include(prologin.concours.stechec.urls)),
    url(r'', include('django_prometheus.urls')),
]

urlpatterns += staticfiles_urlpatterns()
