from django.urls import include, path
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from prologin.djangoconf import set_admin_title

set_admin_title(admin, "Wiki Server")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('notifications/', include('django_nyt.urls')),
    path('', include('wiki.urls')),
]

urlpatterns += staticfiles_urlpatterns()
