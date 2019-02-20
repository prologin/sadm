from django.conf.urls import url

from prologin.concours.oauth import views

urlpatterns = [
    url(r'^autologin$', views.AutoLogin.as_view(), name='autologin'),
    url(r'^callback$',views.Callback.as_view(), name='auth_callback'),
]

