from django.conf.urls import url, include
from rest_framework import routers

from prologin.concours.stechec.restapi import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'champions', views.ChampionViewSet)
router.register(r'tournaments', views.TournamentViewSet)
router.register(r'matches', views.MatchViewSet)
router.register(r'maps', views.MapViewSet)

urlpatterns = [
    # Namespace is important so URLs don't conflict with non-API views
    url(r'^', include(router.urls, namespace='v1')),
]