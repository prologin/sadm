import django.contrib.auth.views
from django.conf import settings
from django.urls import path, include
from django.views.generic import TemplateView

from prologin.concours.stechec import views
from prologin.concours.stechec.forms import LoginForm

champion_patterns = [
    path('<int:pk>/', views.ChampionView.as_view(), name='champion-detail'),
    path('<int:pk>/delete/', views.ConfirmDeleteChampion.as_view(),
         name='champion-delete'),
    path('<int:pk>/sources/', views.ChampionSources.as_view(),
         name='champion-sources'),
    path('all/', views.AllChampionsView.as_view(), name='champions-all'),
    path('mine/', views.MyChampionsView.as_view(), name='champions-mine'),
    path('new/', views.NewChampionView.as_view(), name='champion-new'),
]

match_patterns = [
    path('<int:pk>/', views.MatchView.as_view(), name='match-detail'),
    path('<int:pk>/dump/', views.MatchDumpView.as_view(), name='match-dump'),
    path('<int:pk>/replay/', views.MatchReplayView.as_view(), name='match-replay'),
    path('all/', views.AllMatchesView.as_view(), name='matches-all'),
    path('mine/by-champion/', views.MyChampionMatchesView.as_view(),
         name='matches-mine-by-champion'),
    path('mine/', views.MyMatchesView.as_view(), name='matches-mine'),
    path('new/', views.NewMatchView.as_view(), name='match-new'),

    path('stream/', views.MatchStreamView.as_view(), name='match-stream'),
]

tournament_patterns = [
    path('all/', views.AllTournamentsView.as_view(), name='tournaments-all'),
    path('<int:pk>/', views.TournamentView.as_view(),
         name='tournament-detail'),
    path('<int:pk>/matches/<int:champion>/',
         views.TournamentMatchesView.as_view(),
         name='tournament-matches-view'),
    path('<int:pk>/correct/<int:player>/',
         views.TournamentCorrectView.as_view(),
         name='tournament-correct'),
    path('<int:pk>/correct/<int:player>/delete',
         views.DeleteTournamentCorrectView.as_view(),
         name='delete-tournament-correct'),
    path('<int:pk>/jury-report',
         views.TournamentJuryReportView.as_view(),
         name='tournament-jury-report'),
    path('<int:pk>/print-ranking',
         views.TournamentPrintRankingView.as_view(),
         name='tournament-print-ranking'),
    path('<int:pk>/HallOfFame',
         views.TournamentHallOfFameView.as_view(),
         name='tournament-hall-of-fame'),
]

map_patterns = [
    path('<int:pk>/', views.MapView.as_view(), name='map-detail'),
    path('all/', views.AllMapsView.as_view(), name='maps-all'),
    path('new/', views.NewMapView.as_view(), name='map-new'),
]

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

    path('status/', views.MasterStatus.as_view(), name='status'),

    path('champions/', include(champion_patterns)),
    path('matches/', include(match_patterns)),
    path('tournaments/', include(tournament_patterns)),
]

if settings.STECHEC_USE_MAPS:
    urlpatterns += [
        path('maps/', include(map_patterns)),
    ]
