import contextlib
import json
import os
import re
import tarfile
import tempfile
import glob

from django.conf import settings
from django.urls import reverse
from django.db import models, transaction
from django.utils import timezone
from django.utils.functional import cached_property
from django_prometheus.models import ExportModelOperationsMixin

import prologin.rpc.client
from prologin.concours.stechec.languages import LANGUAGES

stripper_re = re.compile(r'\033\[.*?m')


def strip_ansi_codes(t):
    return stripper_re.sub('', t)


class Map(ExportModelOperationsMixin('map'), models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               related_name='maps',
                               null=True,
                               on_delete=models.CASCADE,
                               verbose_name="auteur")
    name = models.CharField("nom", max_length=100)
    official = models.BooleanField("officielle", default=False)
    ts = models.DateTimeField("date", auto_now_add=True)

    @property
    def maps_dir(self):
        return settings.STECHEC_ROOT / settings.STECHEC_CONTEST / 'maps'

    @property
    def path(self):
        return self.maps_dir / str(self.id)

    @property
    def contents(self):
        return self.path.open().read()

    @contents.setter
    def contents(self, value):
        if value is None:
            return
        self.maps_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
        self.path.open('w').write(value)

    def get_absolute_url(self):
        return reverse("map-detail", kwargs={"pk": self.id})

    def __str__(self):
        return "%s, de %s%s" % (self.name, self.author,
                                " (officielle)" if self.official else "")

    class Meta:
        ordering = ["-official", "-ts"]
        verbose_name = "carte"
        verbose_name_plural = "cartes"


class Champion(ExportModelOperationsMixin('champion'), models.Model):
    SOURCES_FILENAME = 'champion.tgz'
    LOG_FILENAME = 'compilation.log'
    STATUS_CHOICES = (
        ('new', 'En attente de compilation'),
        ('pending', 'En cours de compilation'),
        ('ready', 'Compilé et prêt'),
        ('error', 'Erreur de compilation'),
    )

    name = models.CharField("nom", max_length=100, unique=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               related_name='champions',
                               on_delete=models.CASCADE,
                               verbose_name="auteur")
    status = models.CharField("statut",
                              choices=STATUS_CHOICES,
                              max_length=100,
                              default="new")
    deleted = models.BooleanField("supprimé", default=False)
    comment = models.TextField("commentaire", blank=True)
    ts = models.DateTimeField("date", auto_now_add=True)

    @property
    def directory(self):
        if self.id is None:
            raise RuntimeError(
                "Champion must be saved before accessing its directory")
        contest_dir = settings.STECHEC_ROOT / settings.STECHEC_CONTEST
        return contest_dir / "champions" / self.author.username / str(self.id)

    @property
    def sources_path(self):
        return self.directory / self.SOURCES_FILENAME

    @property
    def sources(self):
        return self.sources_path.open('rb')

    @sources.setter
    def sources(self, uploaded_file):
        if uploaded_file is None:
            return
        self.directory.mkdir(parents=True)
        with self.sources_path.open('wb') as fp:
            for chunk in uploaded_file.chunks():
                fp.write(chunk)

    @property
    def compilation_log(self):
        log_path = self.directory / self.LOG_FILENAME
        try:
            return log_path.open().read()
        except FileNotFoundError:
            return "Log de compilation introuvable."
        except Exception as e:
            return str(e)

    @contextlib.contextmanager
    def _extract_sources(self):
        with tempfile.TemporaryDirectory(prefix='champion-src-') as tmpd:
            with self.sources as tarball:
                with tarfile.open(fileobj=tarball, mode='r:gz') as tar:
                    tar.extractall(tmpd)
                    yield tmpd

    @cached_property
    def language(self):
        with self._extract_sources() as tmpd:
            with open(os.path.join(tmpd, '_lang')) as langf:
                lang_code = langf.read().strip()
        return {'code': lang_code, **LANGUAGES.get(lang_code)}

    @cached_property
    def loc_count_main(self):
        # TODO: use sloccount?
        with self._extract_sources() as tmpd:
            for mainf in glob.glob(os.path.join(tmpd, '[pP]rologin.*')):
                with open(mainf) as f:
                    return len(list(f.readlines()))

    def get_absolute_url(self):
        return reverse('champion-detail', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('champion-delete', kwargs={'pk': self.id})

    def __str__(self):
        return "%s (de %s)" % (self.name, self.author)

    class Meta:
        ordering = ['-ts']
        verbose_name = "champion"
        verbose_name_plural = "champions"


class Tournament(ExportModelOperationsMixin('tournament'), models.Model):
    name = models.CharField("nom", max_length=100)
    ts = models.DateTimeField("date", auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               related_name='tournaments',
                               on_delete=models.CASCADE,
                               verbose_name="créé par")
    players = models.ManyToManyField(Champion,
                                     verbose_name="participants",
                                     related_name='tournaments',
                                     through='TournamentPlayer')
    maps = models.ManyToManyField(Map,
                                  verbose_name="maps",
                                  related_name='tournaments',
                                  through='TournamentMap')
    visible = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tournament-detail", kwargs={"pk": self.id})

    class Meta:
        ordering = ['-ts']
        verbose_name = "tournoi"
        verbose_name_plural = "tournois"


class TournamentPlayer(ExportModelOperationsMixin('tournament_player'),
                       models.Model):
    champion = models.ForeignKey(Champion,
                                 on_delete=models.CASCADE,
                                 related_name='tournamentplayers',
                                 verbose_name="champion")
    tournament = models.ForeignKey(Tournament,
                                   on_delete=models.CASCADE,
                                   related_name='tournamentplayers',
                                   verbose_name="tournoi")
    score = models.IntegerField("score", default=0)

    def __str__(self):
        return "%s pour tournoi %s" % (self.champion, self.tournament)

    class Meta:
        ordering = ["-tournament", "-score"]
        verbose_name = "participant au tournoi"
        verbose_name_plural = "participants au tournoi"


class TournamentMap(ExportModelOperationsMixin('tournament_map'),
                    models.Model):
    map = models.ForeignKey(Map,
                            on_delete=models.CASCADE,
                            verbose_name="carte")
    tournament = models.ForeignKey(Tournament,
                                   on_delete=models.CASCADE,
                                   verbose_name="tournoi")

    def __str__(self):
        return "%s pour tournoi %s" % (self.map, self.tournament)

    class Meta:
        ordering = ["-tournament"]
        verbose_name = "carte utilisée dans le tournoi"
        verbose_name_plural = "cartes utilisées dans le tournoi"


class Match(ExportModelOperationsMixin('match'), models.Model):
    DUMP_FILENAME = "dump.json.gz"
    LOG_FILENAME = "server.log"
    STATUS_CHOICES = (
        ('creating', 'En cours de création'),
        ('new', 'En attente de lancement'),
        ('pending', 'En cours de calcul'),
        ('done', 'Terminé'),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               related_name='matches',
                               on_delete=models.CASCADE,
                               verbose_name="lancé par")
    status = models.CharField("statut",
                              choices=STATUS_CHOICES,
                              max_length=100,
                              default="creating")
    tournament = models.ForeignKey(Tournament,
                                   related_name='matches',
                                   null=True,
                                   blank=True,
                                   on_delete=models.CASCADE,
                                   verbose_name="tournoi")
    players = models.ManyToManyField(Champion,
                                     verbose_name="participants",
                                     related_name='matches',
                                     through='MatchPlayer')
    ts = models.DateTimeField("date", default=timezone.now)
    options = models.CharField("options", max_length=500, default="{}")
    file_options = models.CharField("file_options",
                                    max_length=500,
                                    default="{}")

    @property
    def directory(self):
        hi_id, low_id = divmod(self.id, 1000)
        return (settings.STECHEC_ROOT / settings.STECHEC_CONTEST / "matches" /
                "{:03d}".format(hi_id) / "{:03d}".format(low_id))

    @property
    def log_path(self):
        return self.directory / self.LOG_FILENAME

    @property
    def log(self):
        try:
            return strip_ansi_codes(self.log_path.open().read()).strip()
        except FileNotFoundError:
            return "Log de match introuvable."
        except Exception as e:
            return str(e)

    @property
    def dump_path(self):
        return self.directory / self.DUMP_FILENAME

    @property
    def dump(self):
        try:
            return self.dump_path.open('rb').read()
        except Exception:
            pass

    @property
    def options_dict(self):
        return json.loads(self.options)

    @options_dict.setter
    def options_dict(self, value):
        self.options = json.dumps(value)

    @property
    def file_options_dict(self):
        return json.loads(self.file_options)

    @file_options_dict.setter
    def file_options_dict(self, value):
        self.file_options = json.dumps(value)

    @property
    def map(self):
        try:
            map_id = int(
                self.file_options_dict.get('--map', '').split('/')[-1])
            return Map.objects.get(pk=map_id)
        except Exception:
            return None

    @map.setter
    def map(self, value):
        d = self.file_options_dict
        d['--map'] = str(value)
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

    @classmethod
    def launch_bulk(cls, matches):
        """Launch matches in bulk.

        Args:
            matches (iterable): iterable of dictionaries representing the
                individual matches to launch. Each dictionary has the following
                keys:

                - **author**: the creator of the match
                - **tournament**: optionally, the tournament in which the match
                  is started
                - **map**: optionally, the map of the match if the game is
                  using maps
                - **champions**: an ordered list of Champions fighting in the
                  match

        Returns:
            The list of launched matches.
        """
        ts = timezone.now()

        with transaction.atomic():
            # Bulk create all Match objects
            match_objs = []
            for match in matches:
                m = Match()
                m.author = match['author']
                m.ts = ts
                if 'tournament' in match:
                    m.tournament = match['tournament']
                if 'map' in match:
                    m.map = match['map'].path
                match_objs.append(m)
            # Returning created ids requires PostgreSQL
            created_matches = Match.objects.bulk_create(match_objs)

            # Bulk create all MatchPlayer objects
            player_objs = []
            for i, m in enumerate(created_matches):
                for c in matches[i]['champions']:
                    player_objs.append(MatchPlayer(champion=c, match=m))
            MatchPlayer.objects.bulk_create(player_objs)

            # Update all matches to set them as 'new' (i.e schedule them)
            new_matches_id = [m.id for m in created_matches]
            qs = Match.objects.filter(id__in=new_matches_id)
            qs.update(status='new')
            return qs


class MatchPlayer(ExportModelOperationsMixin('match_player'), models.Model):
    champion = models.ForeignKey(Champion,
                                 related_name='matchplayers',
                                 verbose_name="champion",
                                 on_delete=models.CASCADE)
    match = models.ForeignKey(Match,
                              related_name='matchplayers',
                              verbose_name="match",
                              on_delete=models.CASCADE)
    score = models.IntegerField(default=0, verbose_name="score")

    @property
    def log_path(self):
        return (self.match.directory /
                "log-champ-{}-{}.log".format(self.id, self.champion.id))

    @property
    def log(self):
        try:
            return strip_ansi_codes(self.log_path.open().read()).strip()
        except FileNotFoundError:
            return "Log de match introuvable."
        except Exception as e:
            return str(e)

    def __str__(self):
        return "%s pour match %s" % (self.champion, self.match)

    class Meta:
        ordering = ["-match"]
        verbose_name = "participant à un match"
        verbose_name_plural = "participants à un match"


def master_status():
    rpc = prologin.rpc.client.SyncClient(settings.STECHEC_MASTER,
                                         secret=settings.STECHEC_MASTER_SECRET)
    return rpc.status()
