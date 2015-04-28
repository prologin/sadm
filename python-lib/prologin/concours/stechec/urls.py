from django.conf import settings
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from prologin.concours.stechec.forms import LoginForm
from prologin.concours.stechec import views

urlpatterns = [
    url(r'^$', (TemplateView.as_view(template_name='stechec/home.html')), name="home"),

    url(r'^login/$', auth_views.login, {'template_name': 'stechec/login.html', 'authentication_form': LoginForm}, name="login"),
    url(r'^logout/$', auth_views.logout, {'next_page': '/'}, name="logout"),

    url(r'^ask-help/$', views.AskForHelp.as_view(), name='ask-for-help'),
    url(r'^ask-help/list/$', views.AskForHelpList.as_view(), name='ask-for-help-list'),
    url(r'^report-bug/$', views.ReportBug.as_view(), name='report-bug'),
    url(r'^report-bug/list/$', views.ReportBugList.as_view(), name='report-bug-list'),

    url(r'^champions/(?P<pk>[0-9]+)/$', views.ChampionView.as_view(), name="champion-detail"),
    url(r'^champions/(?P<pk>[0-9]+)/delete/$', login_required(views.ConfirmDeleteChampion.as_view()), name="champion-delete"),
    url(r'^champions/all/$', views.AllChampionsView.as_view(), name="champions-all"),
    url(r'^champions/mine/$', login_required(views.MyChampionsView.as_view()), name="champions-mine"),
    url(r'^champions/new/$', login_required(views.NewChampionView.as_view()), name="champion-new"),

    url(r'^matches/(?P<pk>[0-9]+?)/$', views.MatchView.as_view(), name="match-detail"),
    url(r'^matches/(?P<pk>[0-9]+?)/dump/$', views.MatchDumpView.as_view(), name="match-dump"),
    url(r'^matches/all/$', views.AllMatchesView.as_view(), name="matches-all"),
    url(r'^matches/mine/$', login_required(views.MyMatchesView.as_view()), name="matches-mine"),
    url(r'^matches/new/$', login_required(views.NewMatchView.as_view()), name="match-new"),

    url(r'^status/$', views.MasterStatus.as_view(), name="status"),
]


if settings.STECHEC_USE_MAPS:
    urlpatterns += [
        url(r'^maps/(?P<pk>[0-9]+?)/$', views.MapView.as_view(), name="map-detail"),
        url(r'^maps/all/$', views.AllMapsView.as_view(), name="maps-all"),
        url(r'^maps/new/$', login_required(views.NewMapView.as_view()), name="map-new"),
    ]
