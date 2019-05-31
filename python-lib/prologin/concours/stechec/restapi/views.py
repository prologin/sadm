import collections
import random
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.response import Response
from rest_framework import viewsets, mixins, permissions as rest_permissions
from rest_framework.decorators import action

from prologin.concours.stechec.restapi import (serializers, permissions,
                                               filtering)
from prologin.concours.stechec import models
from prologin.concours.stechec.languages import LANGUAGES


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (get_user_model().objects.all()
                .prefetch_related('maps', 'champions', 'matches'))
    serializer_class = serializers.UserSerializer


class ChampionViewSet(viewsets.ModelViewSet):
    queryset = (models.Champion.objects.filter(deleted=False)
                .select_related('author'))
    serializer_class = serializers.ChampionSerializer
    permission_classes = [permissions.IsOwnerUsing('author')]
    filter_backends = [filtering.IsOwnerUsing('author')]

    def perform_create(self, serializer):
        champion = serializer.save(author=self.request.user, sources=None)
        # This is a special setter
        champion.sources = serializer.validated_data['sources']


class MapViewSet(viewsets.ModelViewSet):
    queryset = models.Map.objects.all().select_related('author')
    serializer_class = serializers.MapSerializer
    permission_classes = [permissions.IsOwnerUsing('author')]
    filter_backends = [filtering.IsOwnerUsing('author')]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MatchViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = (models.Match.objects
                .select_related('author')
                .prefetch_related('players__author', 'matchplayers'))
    serializer_class = serializers.MatchSerializer
    # permission_classes = [permissions.IsOwnerUsing('author')]
    # filter_backends = [filtering.IsOwnerUsing('author')]

    def get_context(self, *args, **kwargs):
        ctx = super().get_context(*args, **kwargs)
        ctx['display_edit_forms'] = False
        return ctx

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.CreateMatchSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        # This is a bit hacky. We can't call serializer.save() because
        # there are custom non-model attributes (map, champion_N) in it.
        data = {'author': self.request.user, 'status': 'creating'}

        # So we rollback if either create() or later changes fail
        with transaction.atomic():
            match = serializer.instance = serializer.create(data)
            # match is a saved Match with an id
            with transaction.atomic():
                if settings.STECHEC_USE_MAPS:
                    match.map = serializer.validated_data['map'].path

                for i in range(1, settings.STECHEC_NPLAYERS + 1):
                    champion = serializer.validated_data['champion_%d' % i]
                    player = models.MatchPlayer(champion=champion,
                                                match=match)
                    player.save()

                match.status = 'new'
                match.save()

    @action(['get'], detail=False)
    def interesting(self, request):
        matches = list(self.get_queryset()
                       .annotate(sum_scores=Sum('matchplayers__score'))
                       .order_by('-sum_scores'))
        if len(matches) > 50:
            # Only take the 33% most interesting
            matches = matches[:len(matches) // 3 + 1]
        random.shuffle(matches)
        serializer = self.get_serializer(matches, many=True)
        return Response(serializer.data)


class TournamentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (models.Tournament.objects.all()
                .select_related('author')
                .prefetch_related('matches'))
    serializer_class = serializers.TournamentSerializer
    permission_classes = [rest_permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(visible=True)
        return qs

    def get_stats(self):
        tournament = self.get_object()

        champions = {}
        tournaments = (tournament.tournamentplayers
                       .prefetch_related('champion__author'))
        for p in tournaments:
            champion = p.champion
            champions[champion.id] = {
                'name': champion.name,
                'author': champion.author.username,
                'sloc': champion.loc_count_main,
                'language': champion.language,
                'tournament_score': p.score,
                'sum_match_score': 0,
                'avg_match_score': 0,
                'num_matches': 0,
            }
        for mp in (models.MatchPlayer.objects
                   .filter(match__tournament=tournament,
                           match__status='done')):
            champions[mp.champion_id]['num_matches'] += 1
            champions[mp.champion_id]['sum_match_score'] += mp.score
        for c in champions.values():
            if c['num_matches']:
                c['avg_match_score'] = c['sum_match_score'] / c['num_matches']
        return list(champions.values())

    @action(['get'], detail=True)
    def stats(self, request, pk):
        return Response(self.get_stats())

    @action(['get'], detail=True)
    def plot_sloc(self, request, pk):
        stats = self.get_stats()
        series = collections.defaultdict(list)
        for c in stats:
            series[c['language']['code']].append({
                'name': c['name'],
                'author': c['author'],
                'x': c['sloc'],
                'y': c['tournament_score'],
            })
        series = [{'name': LANGUAGES[k]['name'], 'data': v,
                   **({'color': LANGUAGES[k]['color']}
                      if k in LANGUAGES else {})}
                  for k, v in series.items()]
        return Response(series)

    @action(['get'], detail=True)
    def lang_share(self, request, pk):
        stats = self.get_stats()
        counter = collections.Counter(c['language']['code'] for c in stats)
        data = [{'name': LANGUAGES[k]['name'], 'y': v,
                 **({'color': LANGUAGES[k]['color']}
                    if k in LANGUAGES else {})}
                for k, v in counter.items()]
        return Response(data)

    @method_decorator(cache_page(60 * 5))  # 5 minutes cache
    @action(['get'], detail=False)
    def evolution(self, request):
        tournaments = (
            self.get_queryset()
            .order_by('id')
            .prefetch_related('tournamentplayers__champion__author')
            .prefetch_related('players__author'))
        users = {c.author.username
                 for t in tournaments for c in t.players.all()}
        rankings = {u: [None] * len(tournaments) for u in users}
        for tid, tournament in enumerate(tournaments):
            players = sorted(tournament.tournamentplayers.all(),
                             key=lambda p: -p.score)
            for rank, p in enumerate(players, 1):
                rankings[p.champion.author.username][tid] = rank

        series = [{'name': k, 'data': v, 'visible': False}
                  for k, v in sorted(rankings.items(),
                                     key=lambda x: x[1][-1])]
        categories = [t.name for t in tournaments]
        return Response({'series': series, 'categories': categories})
