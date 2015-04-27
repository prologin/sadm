# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db import models

from prometheus_client import Gauge
from django_prometheus.models import ExportModelOperationsMixin

import json
import os.path
import re

import prologin.rpc.client

stripper_re = re.compile(r'\033\[.*?m')
def strip_ansi_codes(t):
    return stripper_re.sub('', t)


class Map(ExportModelOperationsMixin('map'), models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="auteur")
    name = models.CharField("nom", max_length=100)
    official = models.BooleanField("officielle", default=False)
    ts = models.DateTimeField("date", auto_now_add=True)

    @property
    def path(self):
        contest_dir = os.path.join(settings.STECHEC_ROOT, settings.STECHEC_CONTEST)
        maps_dir = os.path.join(contest_dir, "maps")
        return os.path.join(maps_dir, "{}".format(self.id))

    @property
    def contents(self):
        return open(self.path, encoding='utf-8').read()

    @contents.setter
    def contents(self, value):
        open(self.path, 'w', encoding='utf-8').write(value)

    def get_absolute_url(self):
        return reverse("map-detail", kwargs={"pk": self.id})

    def __str__(self):
        return "%s, de %s%s" % (self.name, self.author,
                                " (officielle)" if self.official else "")

    class Meta:
        ordering = ["-official", "-ts"]
        verbose_name = "map"
        verbose_name_plural = "maps"


class Champion(ExportModelOperationsMixin('champion'), models.Model):
    STATUS_CHOICES = (
        ('new', 'En attente de compilation'),
        ('pending', 'En cours de compilation'),
        ('ready', 'Compilé et prêt'),
        ('error', 'Erreur de compilation'),
    )

    name = models.CharField("nom", max_length=100)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="auteur")
    status = models.CharField("statut", choices=STATUS_CHOICES,
                              max_length=100, default="new")
    deleted = models.BooleanField("supprimé", default=False)
    comment = models.TextField("commentaire")
    ts = models.DateTimeField("date", auto_now_add=True)

    @property
    def directory(self):
        contest_dir = os.path.join(settings.STECHEC_ROOT, settings.STECHEC_CONTEST)
        champions_dir = os.path.join(contest_dir, "champions")
        return os.path.join(champions_dir, self.author.username, str(self.id))

    @property
    def compilation_log(self):
        this_dir = self.directory
        log_path = os.path.join(this_dir, "compilation.log")
        if os.path.exists(log_path):
            try:
                return open(log_path, encoding='utf-8').read()
            except Exception as e:
                return str(e)
        else:
            return "Log de compilation introuvable."

    def get_absolute_url(self):
        return reverse('champion-detail', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('champion-delete', kwargs={'pk': self.id})

    def __str__(self):
        return "%s, de %s" % (self.name, self.author)

    class Meta:
        ordering = ['-ts']
        verbose_name = "champion"
        verbose_name_plural = "champions"


class Tournament(ExportModelOperationsMixin('tournament'), models.Model):
    name = models.CharField("nom", max_length=100)
    ts = models.DateTimeField("date", auto_now_add=True)
    players = models.ManyToManyField(Champion, verbose_name="participants",
                                     through="TournamentPlayer")
    maps = models.ManyToManyField(Map, verbose_name="maps",
                                     through="TournamentMap")

    def __str__(self):
        return "%s, %s" % (self.name, self.ts)

    class Meta:
        ordering = ['-ts']
        verbose_name = "tournoi"
        verbose_name_plural = "tournois"


class TournamentPlayer(ExportModelOperationsMixin('tournament_player'),
                       models.Model):
    champion = models.ForeignKey(Champion, verbose_name="champion")
    tournament = models.ForeignKey(Tournament, verbose_name="tournoi")
    score = models.IntegerField("score", default=0)

    def __str__(self):
        return "%s pour tournoi %s" % (self.champion, self.tournament)

    class Meta:
        ordering = ["-tournament", "-score"]
        verbose_name = "participant à un tournoi"
        verbose_name_plural = "participants à un tournoi"


class TournamentMap(ExportModelOperationsMixin('tournament_map'), models.Model):
    map = models.ForeignKey(Map, verbose_name="map")
    tournament = models.ForeignKey(Tournament, verbose_name="tournoi")

    def __str__(self):
        return "%s pour tournoi %s" % (self.map, self.tournament)

    class Meta:
        ordering = ["-tournament"]
        verbose_name = "map utilisée dans un tournoi"
        verbose_name_plural = "maps utilisées dans un tournoi"


class Match(ExportModelOperationsMixin('match'), models.Model):
    STATUS_CHOICES = (
        ('creating', 'En cours de création'),
        ('new', 'En attente de lancement'),
        ('pending', 'En cours de calcul'),
        ('done', 'Terminé'),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="lancé par")
    status = models.CharField("statut", choices=STATUS_CHOICES, max_length=100,
                              default="creating")
    tournament = models.ForeignKey(Tournament, verbose_name="tournoi",
                                   null=True, blank=True)
    players = models.ManyToManyField(Champion, verbose_name="participants",
                                     through="MatchPlayer")
    ts = models.DateTimeField("date", auto_now_add=True)
    options = models.CharField("options", max_length=500, default="{}")
    file_options = models.CharField("file_options", max_length=500, default="{}")

    @property
    def directory(self):
        contest_dir = os.path.join(settings.STECHEC_ROOT, settings.STECHEC_CONTEST)
        matches_dir = os.path.join(contest_dir, "matches")
        hi_id = "%03d" % (self.id / 1000)
        low_id = "%03d" % (self.id % 1000)
        return os.path.join(matches_dir, hi_id, low_id)

    @property
    def log(self):
        log_path = os.path.join(self.directory, "server.log")
        if os.path.exists(log_path):
            try:
                t = open(log_path, encoding='utf-8').read()
                return strip_ansi_codes(t)
            except Exception as e:
                return str(e)
        else:
            return "Log de match introuvable."

    @property
    def dump(self):
        dump_path = os.path.join(self.directory, "dump.json.gz")
        return open(dump_path, "rb").read()

    @property
    def options_dict(self):
        return json.loads(self.options)

    @options_dict.setter
    def options_dict(self, value):
        self.options = json.dumps(value)

    @property
    def file_options_dict(self):
        return json.loads(self.file_options)

    @options_dict.setter
    def file_options_dict(self, value):
        self.file_options = json.dumps(value)

    @property
    def map(self):
        return self.file_options_dict.get('--map', '')

    @map.setter
    def map(self, value):
        d = self.file_options_dict
        d['--map'] = value
        self.file_options_dict = d

    @property
    def is_done(self):
        return self.status == 'done'

    def get_absolute_url(self):
        return reverse('match-detail', kwargs={'pk': self.id})

    def __str__(self):
        return "%s (par %s)" % (self.ts, self.author)

    class Meta:
        ordering = ["-ts"]
        verbose_name = "match"
        verbose_name_plural = "matches"

# Monitoring
concours_match_status_count = Gauge(
    'concours_match_status_count',
    'Count of matches in by status',
    labelnames=('status',))
for status in ('creating', 'new', 'pending', 'done'):
    labels = {'status': status}
    concours_match_status_count.labels(labels).set_function(
        lambda status=status: len(Match.objects.filter(status=status)))

class MatchPlayer(ExportModelOperationsMixin('match_player'), models.Model):
    champion = models.ForeignKey(Champion, verbose_name="champion")
    match = models.ForeignKey(Match, verbose_name="match")
    score = models.IntegerField("score", default=0)

    @property
    def log(self):
        filename = "log-champ-%d-%d.log" % (self.id, self.champion.id)
        log_path = os.path.join(self.match.directory, filename)
        if os.path.exists(log_path):
            try:
                t = open(log_path, encoding='utf-8').read()
                return strip_ansi_codes(t)
            except Exception as e:
                return str(e)
        return "Log de match introuvable."

    def __str__(self):
        return "%s pour match %s" % (self.champion, self.match)

    class Meta:
        ordering = ["-match"]
        verbose_name = "participant à un match"
        verbose_name_plural = "participants à un match"


def master_status():
    rpc = prologin.rpc.client.Client(settings.STECHEC_MASTER,
                                     secret=settings.STECHEC_MASTER_SECRET)
    return rpc.status()
