import django.contrib.auth.views
from django.conf import settings
from django.urls import path
from django.views.generic import TemplateView

from prologin.concours.stechec import views
from prologin.concours.stechec.forms import LoginForm

urlpatterns = [
    path('', (TemplateView.as_view(template_name='stechec/home.html')),
         name="home"),
    path('login/',
         django.contrib.auth.views.LoginView.as_view(
             template_name='stechec/login.html',
             authentication_form=LoginForm),
         name="login"),
    path('logout/',
         django.contrib.auth.views.LogoutView.as_view(next_page='/'),
         name="logout"),
    path('ask-help/', views.AskForHelp.as_view(), name='ask-for-help'),
    path('ask-help/list/',
         views.AskForHelpList.as_view(),
         name='ask-for-help-list'),
    path('report-bug/', views.ReportBug.as_view(), name='report-bug'),
    path('report-bug/list/',
         views.ReportBugList.as_view(),
         name='report-bug-list'),

    path('champions/<int:pk>/',
         views.ChampionView.as_view(),
         name='champion-detail'),
    path('champions/<int:pk>/delete/',
         views.ConfirmDeleteChampion.as_view(),
         name='champion-delete'),
    path('champions/<int:pk>/sources/',
         views.ChampionSources.as_view(),
         name='champion-sources'),
    path('champions/all/',
         views.AllChampionsView.as_view(),
         name='champions-all'),
    path('champions/mine/',
         views.MyChampionsView.as_view(),
         name='champions-mine'),
    path('champions/new/',
         views.NewChampionView.as_view(),
         name='champion-new'),

    path('matches/<int:pk>/', views.MatchView.as_view(), name='match-detail'),
    path('matches/<int:pk>/dump/',
         views.MatchDumpView.as_view(),
         name='match-dump'),
    path('matches/all/', views.AllMatchesView.as_view(), name='matches-all'),
    path('matches/mine/by-champion/',
         views.MyChampionMatchesView.as_view(),
         name='matches-mine-by-champion'),
    path('matches/mine/', views.MyMatchesView.as_view(), name='matches-mine'),
    path('matches/new/', views.NewMatchView.as_view(), name='match-new'),

    path('tournaments/all/', views.AllTournamentsView.as_view(),
         name='tournaments-all'),
    path('tournaments/<int:pk>/', views.TournamentView.as_view(),
         name='tournament-detail'),
    path('tournaments/<int:pk>/matches/<int:champion>/',
         views.TournamentMatchesView.as_view(),
         name='tournament-matches-view'),

    path('status/', views.MasterStatus.as_view(), name='status'),
]

if settings.STECHEC_USE_MAPS:
    urlpatterns += [
        path('maps/<int:pk>/', views.MapView.as_view(), name='map-detail'),
        path('maps/all/', views.AllMapsView.as_view(), name='maps-all'),
        path('maps/new/', views.NewMapView.as_view(), name='map-new'),
    ]
