from django.conf.urls import include, url
from django.contrib import admin

import prologin.concours.stechec.urls

urlpatterns = [
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include(prologin.concours.stechec.urls)),
]
