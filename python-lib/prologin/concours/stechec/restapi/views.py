from rest_framework import viewsets, mixins, permissions as rest_permissions

from prologin.concours.stechec.restapi import serializers, permissions, filtering
from prologin.concours.stechec import models, forms
from django.forms import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction


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
        champion.sources = serializer.validated_data['sources']  # this is a special setter


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


class MapViewSet(viewsets.ModelViewSet):
    queryset = models.Map.objects.all()
    serializer_class = serializers.MapSerializer
    permission_classes = [permissions.IsOwnerUsing('author')]
    filter_backends = [filtering.IsOwnerUsing('author')]

    def perform_create(self, serializer):
        map = serializer.save(author=self.request.user, contents=None)
        map.contents = serializer.validated_data['contents']  # this is a special setter
