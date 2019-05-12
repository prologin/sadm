from django.contrib import admin
from django.conf import settings
from django.utils.safestring import mark_safe
from prologin.concours.stechec import models

admin.site.register(models.Champion)


class MatchPlayerInline(admin.TabularInline):
    model = models.Match.players.through


@admin.register(models.Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'status', 'player_list', 'ts')
    list_filter = ('status', 'tournament')
    inlines = [MatchPlayerInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('players')

    @mark_safe
    def player_list(self, obj):
        return ' vs '.join(['<a href="{}">{}</a>'.format(c.get_absolute_url(), c)
                            for c in obj.players.all()])


@admin.register(models.Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'ts')


if settings.STECHEC_USE_MAPS:
    admin.site.register(models.Map)
    admin.site.register(models.TournamentMap)
