from django.conf import settings
from django.conf.urls import url
# from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from prologin.concours.stechec import views

urlpatterns = [
    url(r'^$', (TemplateView.as_view(template_name='stechec/home.html')), name="home"),
    # url(r'^login/$', auth_views.login, {'template_name': 'stechec/login.html'}, name="login"),
    # url(r'^logout/$', auth_views.logout, {'next_page': '/'}, name="logout"),

    url(r'^champions/(?P<pk>[0-9]+)/$', views.ChampionView.as_view(), name="champion-detail"),
    url(r'^champions/(?P<pk>[0-9]+)/delete/$', views.ConfirmDeleteChampion.as_view(), name="champion-delete"),
    url(r'^champions/all/$', views.AllChampionsView.as_view(), name="champions-all"),
    url(r'^champions/mine/$', views.MyChampionsView.as_view(), name="champions-mine"),
    url(r'^champions/new/$', views.NewChampionView.as_view(), name="champion-new"),

    url(r'^matches/(?P<pk>[0-9]+?)/$', views.MatchView.as_view(), name="match-detail"),
    url(r'^matches/(?P<pk>[0-9]+?)/dump/$', views.match_dump, name="match-dump"),
    url(r'^matches/all/$', views.AllMatchesView.as_view(), name="matches-all"),
    url(r'^matches/mine/$', views.MyMatchesView.as_view(), name="matches-mine"),
    url(r'^matches/new/$', views.NewMatchView.as_view(), name="match-new"),

    url(r'^status/$', views.MasterStatus.as_view(), name="status"),
]


if settings.STECHEC_USE_MAPS:
    urlpatterns += [
        url(r'^maps/(?P<pk>[0-9]+?)/$', views.MapView.as_view(), name="map-detail"),
        url(r'^maps/all/$', views.AllMapsView.as_view(), name="maps-all"),
        url(r'^maps/new/$', views.NewMapView.as_view(), name="map-new"),
    ]
