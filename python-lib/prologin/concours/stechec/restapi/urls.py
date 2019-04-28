from django.conf import settings
from django.urls import path, include
from rest_framework import routers

from prologin.concours.stechec.restapi import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'champions', views.ChampionViewSet)
router.register(r'tournaments', views.TournamentViewSet)
router.register(r'matches', views.MatchViewSet)

if settings.STECHEC_USE_MAPS:
    router.register(r'maps', views.MapViewSet)

urlpatterns = [
    # Namespace is important so URLs don't conflict with non-API views
    path('', include((router.urls, 'restapi'), namespace='v1')),
]
