from django.contrib import admin
from django.conf import settings
from prologin.concours.stechec import models

admin.site.register(models.Champion)
admin.site.register(models.Tournament)
admin.site.register(models.TournamentPlayer)
admin.site.register(models.Match)
admin.site.register(models.MatchPlayer)

if settings.STECHEC_USE_MAPS:
    admin.site.register(models.Map)
    admin.site.register(models.TournamentMap)
