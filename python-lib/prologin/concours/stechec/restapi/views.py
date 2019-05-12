import collections
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.response import Response
from rest_framework import viewsets, mixins, permissions as rest_permissions
from rest_framework.decorators import detail_route

from prologin.concours.stechec.restapi import (serializers, permissions,
                                               filtering)
from prologin.concours.stechec import models
from prologin.concours.stechec.languages import LANGUAGES


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = serializers.UserSerializer


class ChampionViewSet(viewsets.ModelViewSet):
    queryset = models.Champion.objects.filter(deleted=False)
    serializer_class = serializers.ChampionSerializer
    permission_classes = [permissions.IsOwnerUsing('author')]
    filter_backends = [filtering.IsOwnerUsing('author')]

    def perform_create(self, serializer):
        champion = serializer.save(author=self.request.user, sources=None)
        # This is a special setter
        champion.sources = serializer.validated_data['sources']


class MatchViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = models.Match.objects.all()
    serializer_class = serializers.MatchSerializer
    permission_classes = [permissions.IsOwnerUsing('author')]
    filter_backends = [filtering.IsOwnerUsing('author')]

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


class TournamentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Tournament.objects.all()
    serializer_class = serializers.TournamentSerializer
    permission_classes = [rest_permissions.IsAuthenticated]

    def get_stats(self):
        tournament = self.get_object()

        champions = {}
        for p in tournament.tournamentplayers.prefetch_related('champion'):
            champion = p.champion
            champions[champion.id] = {
                'name': champion.name,
                'author': champion.author.username,
                'sloc': champion.loc_count_main,
                'language': champion.lang_code,
                'tournament_score': p.score,
                'sum_match_score': 0,
                'avg_match_score': 0,
                'num_matches': 0,
            }
        for mp in (models.MatchPlayer.objects
                   .filter(match__tournament=tournament,
                           match__status='done')):
            champions[mp.champion.id]['num_matches'] += 1
            champions[mp.champion.id]['sum_match_score'] += mp.score
        for c in champions.values():
            c['avg_match_score'] = c['sum_match_score'] // c['num_matches']
        return list(champions.values())

    @detail_route(['get'], url_path='stats')
    def stats(self, request, pk):
        return Response(self.get_stats())

    @detail_route(['get'], url_path='plot_sloc')
    def plot_sloc(self, request, pk):
        stats = self.get_stats()
        series = collections.defaultdict(list)
        for c in stats:
            series[c['language']].append({
                'name': c['name'],
                'author': c['author'],
                'x': c['sloc'],
                'y': c['avg_match_score'],
            })
        series = [{'name': LANGUAGES[k]['name'],
                   'color': LANGUAGES[k]['color'],
                   'data': v}
                  for k, v in series.items()]
        return Response(series)


class MapViewSet(viewsets.ModelViewSet):
    queryset = models.Map.objects.all()
    serializer_class = serializers.MapSerializer
    permission_classes = [permissions.IsOwnerUsing('author')]
    filter_backends = [filtering.IsOwnerUsing('author')]

    def perform_create(self, serializer):
        map = serializer.save(author=self.request.user, contents=None)
        # This is a special setter
        map.contents = serializer.validated_data['contents']
