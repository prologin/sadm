from prologin.concours.stechec import models
from django.contrib import admin

admin.site.register(models.Map)
admin.site.register(models.Champion)
admin.site.register(models.Tournament)
admin.site.register(models.TournamentPlayer)
admin.site.register(models.TournamentMap)
admin.site.register(models.Match)
admin.site.register(models.MatchPlayer)
