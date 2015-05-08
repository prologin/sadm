from rest_framework import serializers

from django.forms import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from prologin.concours.stechec import models, forms
from django.contrib.auth import get_user_model
from django.conf import settings


class MinimalUserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        read_only_fields = ('url', 'id', 'username')
        fields = read_only_fields


class ChampionSerializer(serializers.HyperlinkedModelSerializer):
    author = MinimalUserSerializer(read_only=True)
    sources = serializers.FileField(write_only=True)
    status_human = serializers.ReadOnlyField(source='get_status_display')
    created = serializers.DateTimeField(source='ts', read_only=True)

    class Meta:
        model = models.Champion
        read_only_fields = ('url', 'id', 'author', 'status', 'status_human', 'created')
        fields = read_only_fields + ('name', 'sources', 'comment')


class MatchSerializer(serializers.HyperlinkedModelSerializer):
    author = MinimalUserSerializer(read_only=True)
    status_human = serializers.ReadOnlyField(source='get_status_display')
    created = serializers.DateTimeField(source='ts', read_only=True)

    class Meta:
        model = models.Match
        read_only_fields = ('url', 'id', 'author', 'status', 'status_human', 'tournament', 'players', 'created')
        fields = read_only_fields


class CreateMatchSerializer(serializers.HyperlinkedModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for i in range(1, settings.STECHEC_NPLAYERS + 1):
            f = serializers.PrimaryKeyRelatedField(queryset=models.Champion.objects.all(), write_only=True)
            self.fields['champion_%d' % i] = f

        if settings.STECHEC_USE_MAPS:
            self.fields['map'] = serializers.PrimaryKeyRelatedField(queryset=models.Map.objects.all(), write_only=True)

    class Meta:
        model = models.Match
        # We add url to add a Location header in the 201 CREATED response
        read_only_fields = ('url',)
        fields = read_only_fields


class MapContentsField(serializers.CharField):
    """
    Small wrapper around forms.MapCreationForm.clean_validate_contents
    """
    def to_representation(self, obj):
        try:
            return forms.MapCreationForm.clean_validate_contents(obj)
        except ValidationError as e:
            raise DRFValidationError(e.message)


class MapSerializer(serializers.HyperlinkedModelSerializer):
    author = MinimalUserSerializer(read_only=True)
    created = serializers.DateTimeField(source='ts', read_only=True)
    # contents is required because it's not a model field
    contents = MapContentsField(style={'base_template': 'textarea.html'})

    class Meta:
        model = models.Map
        read_only_fields = ('url', 'id', 'author', 'official', 'created')
        fields = read_only_fields + ('name', 'contents')


class TournamentSerializer(serializers.ModelSerializer):
    players = ChampionSerializer(many=True, read_only=True)
    maps = MapSerializer(many=True, read_only=True)
    matches = MatchSerializer(many=True, read_only=True)
    created = serializers.DateTimeField(source='ts', read_only=True)

    class Meta:
        model = models.Tournament
        read_only_fields = ('name', 'players', 'maps', 'matches', 'created')
        fields = read_only_fields


class UserSerializer(serializers.HyperlinkedModelSerializer):
    maps = MapSerializer(many=True, read_only=True)
    matches = MatchSerializer(many=True, read_only=True)
    champions = ChampionSerializer(many=True, read_only=True)

    class Meta:
        model = get_user_model()
        read_only_fields = ('url', 'id', 'username', 'maps', 'matches', 'champions')
        fields = read_only_fields
