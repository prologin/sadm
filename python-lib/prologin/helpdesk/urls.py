from django.urls import include, path
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from prologin.djangoconf import set_admin_title

set_admin_title(admin, "Helpdesk")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('helpdesk.urls', namespace='helpdesk')),
]

urlpatterns += staticfiles_urlpatterns()
