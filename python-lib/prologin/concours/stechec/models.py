import contextlib
import io
import json
import os
import re
import tarfile
import tempfile
import glob

import matplotlib.pyplot as plt
import numpy as np

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.files.images import ImageFile
from django.db import models
from django.utils import timezone
from django_prometheus.models import ExportModelOperationsMixin

from collections import defaultdict

import prologin.rpc.client

stripper_re = re.compile(r'\033\[.*?m')


def strip_ansi_codes(t):
    return stripper_re.sub('', t)


class Map(ExportModelOperationsMixin('map'), models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='maps', verbose_name="auteur")
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
        if self.maps_dir.is_dir():
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
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='champions', verbose_name="auteur")
    status = models.CharField("statut", choices=STATUS_CHOICES,
                              max_length=100, default="new")
    deleted = models.BooleanField("supprimé", default=False)
    comment = models.TextField("commentaire", blank=True)
    ts = models.DateTimeField("date", auto_now_add=True)

    @property
    def directory(self):
        if self.id is None:
            raise RuntimeError("Champion must be saved before accessing its directory")
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
            if isinstance(uploaded_file, bytes):
                fp.write(uploaded_file)
            else:
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
        with tempfile.TemporaryDirectory(prefix='lang-check-') as tmpd:
            with self.sources as tarball:
                with tarfile.open(fileobj=tarball, mode='r:gz') as tar:
                    tar.extractall(tmpd)
                    yield tmpd

    def get_lang_code(self):
        with self._extract_sources() as tmpd:
            with open(os.path.join(tmpd, '_lang')) as langf:
                return langf.read().strip()

    def get_main_loc_count(self):
        with self._extract_sources() as tmpd:
            for mainf in glob.glob(os.path.join(tmpd, '[pP]rologin.*')):
                with open(mainf) as f:
                    return len(list(f.readlines()))

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
                                     related_name='tournaments',
                                     through='TournamentPlayer')
    maps = models.ManyToManyField(Map, verbose_name="maps",
                                  related_name='tournaments',
                                  through='TournamentMap')
    is_finished = models.BooleanField(default=False)
    is_calculated = models.BooleanField(default=False)
    graphic_lang = models.ImageField(upload_to='graph/', null=True)
    graphic_loc = models.ImageField(upload_to='graph/', null=True)
    graphic_repartition = models.ImageField(upload_to='graph/', null=True)

    def __str__(self):
        return "%s, %s" % (self.name, self.ts)

    def get_absolute_url(self):
        return reverse("tournament-detail", kwargs={"pk": self.id})

    def evaluate_is_finished(self):
        matchs = Match.objects.filter(tournament=self)
        matchs_done = Match.objects.filter(tournament=self, status='done')
        self.is_finished = len(matchs)==len(matchs_done)

    def compute_stat(self):
        matchs = Match.objects.filter(tournament=self)
        nb_player_language = defaultdict(int)
        score_language = defaultdict(int)
        nb_player_nb_lignes = defaultdict(int)
        score_nb_lignes = defaultdict(int)

        tournament_players = TournamentPlayer.objects.filter(tournament=self)
        for tournament_player in tournament_players:
            tournament_player.score = 0
            tournament_player.nb_timeout = 0
            tournament_player.save()
        #Iterate over all matchs to create score board and save data
        for match in matchs:
            log = match.log
            log_split = log.split("\n")
            nb_timeout = []
            for line in log_split :
                if line=='---':
                    pass
                else :
                    field,result = line.split(" ")
                    if field == "nb_timeout:":
                        nb_timeout.append(int(result))
            i_champion = 0
            for champion in match.players.all():
                player = MatchPlayer.objects.filter(match=match,champion=champion).first()
                tournament_player,created = TournamentPlayer.objects.get_or_create(tournament=self, champion=champion)
                tournament_player.score += player.score
                tournament_player.nb_timeout += nb_timeout[i_champion]
                tournament_player.save()
                i_champion += 1
                nb_player_language[champion.get_lang_code()] += 1
                score_language[champion.get_lang_code()] += player.score
                nb_player_nb_lignes[champion.get_main_loc_count()] += 1
                score_nb_lignes[champion.get_main_loc_count()] += player.score

        tournament_players = TournamentPlayer.objects.filter(tournament=self)
        nb_matchs_per_player = 2*len(matchs)/len(tournament_players)
        for tournament_player in tournament_players:
            tournament_player.score =  tournament_player.score/nb_matchs_per_player
            tournament_player.save()

        # Average score per language
        img_fig = io.BytesIO()
        fig = plt.figure()
        ax = fig.add_subplot(111)
        names = [ k for k in sorted(nb_player_language)]
        frequencies = [score_language[k]/nb_player_language[k] for k in sorted(nb_player_language)]

        x_coordinates = np.arange(len(names))
        ax.bar(x_coordinates, frequencies, align='center')

        ax.xaxis.set_major_locator(plt.FixedLocator(x_coordinates))
        ax.xaxis.set_major_formatter(plt.FixedFormatter(names))

        plt.xlabel("Langage")
        plt.ylabel("Average score")
        fig.savefig(img_fig, format="svg", bbox_inches='tight', transparent=True)
        img_file = ImageFile(img_fig)
        self.graphic_lang.save("lang.svg",img_file)

        # Average score per number of lines
        img_fig = io.BytesIO()
        fig = plt.figure()
        nb_lignes = [ k for k in sorted(nb_player_nb_lignes)]
        average_score_line = []
        average_line = []
        window_size = 100
        start = 0
        for window in range(0,max(nb_lignes)+1,window_size):
            cpt = 0
            sum_score = 0
            while(start < len(nb_lignes) and nb_lignes[start] <= window+window_size):
                cpt += nb_player_nb_lignes[nb_lignes[start]]
                sum_score += score_nb_lignes[nb_lignes[start]]
                start += 1
            if cpt > 0:
                average_line.append(window+window_size/2)
                average_score_line.append(sum_score/cpt)
        plt.plot(average_line,average_score_line)
        plt.xlabel("Number of line")
        plt.ylabel("Average score")
        fig.savefig(img_fig, format="svg", bbox_inches='tight', transparent=True)
        img_file = ImageFile(img_fig)
        self.graphic_loc.save("loc.svg",img_file)

        # Repartition of the candidates depending on their score
        img_fig = io.BytesIO()
        fig = plt.figure()
        ax = fig.add_subplot(111)
        histo_score = []
        histo_nb_candidates = []
        tournament_players = TournamentPlayer.objects.filter(tournament=self)
        players = [player.score for player in tournament_players]
        players.sort()
        window_size = int((max(players)+1)/10)
        start = 0
        for window in range(0,max(players)+1,window_size):
            cpt = 0
            sum_score = 0
            while(start < len(players) and players[start] <= window+window_size):
                cpt += 1
                start += 1
            histo_score.append(window+window_size/2)
            histo_nb_candidates.append(cpt)

        x_coordinates = np.arange(len(histo_score))
        ax.bar(x_coordinates, histo_nb_candidates, align='center')

        ax.xaxis.set_major_locator(plt.FixedLocator([x_coordinates[i] for i in range(0, len(x_coordinates),2)]))
        ax.xaxis.set_major_formatter(plt.FixedFormatter([histo_score[i] for i in range(0, len(histo_score),2)]))

        plt.xlabel("Score")
        plt.ylabel("Nombre de candidats")
        fig.savefig(img_fig, format="svg", bbox_inches='tight', transparent=True)
        img_file = ImageFile(img_fig)
        self.graphic_repartition.save("repartition.svg",img_file)


    class Meta:
        ordering = ['-ts']
        verbose_name = "tournoi"
        verbose_name_plural = "tournois"


class TournamentPlayer(ExportModelOperationsMixin('tournament_player'),
                       models.Model):
    champion = models.ForeignKey(Champion, verbose_name="champion")
    tournament = models.ForeignKey(Tournament, verbose_name="tournoi")
    score = models.IntegerField("score", default=0)
    nb_timeout = models.IntegerField("nombre de timeout", default=0)

    def __str__(self):
        return "%s pour tournoi %s" % (self.champion, self.tournament)

    class Meta:
        ordering = ["-tournament", "-score"]
        verbose_name = "participant à un tournoi"
        verbose_name_plural = "participants à un tournoi"


class TournamentMap(ExportModelOperationsMixin('tournament_map'), models.Model):
    map = models.ForeignKey(Map, verbose_name="carte")
    tournament = models.ForeignKey(Tournament, verbose_name="tournoi")

    def __str__(self):
        return "%s pour tournoi %s" % (self.map, self.tournament)

    class Meta:
        ordering = ["-tournament"]
        verbose_name = "carte utilisée dans un tournoi"
        verbose_name_plural = "cartes utilisées dans un tournoi"


class Match(ExportModelOperationsMixin('match'), models.Model):
    DUMP_FILENAME = "dump.json.gz"
    LOG_FILENAME = "server.log"
    STATUS_CHOICES = (
        ('creating', 'En cours de création'),
        ('new', 'En attente de lancement'),
        ('pending', 'En cours de calcul'),
        ('done', 'Terminé'),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='matches', verbose_name="lancé par")
    status = models.CharField("statut", choices=STATUS_CHOICES, max_length=100,
                              default="creating")
    tournament = models.ForeignKey(Tournament, verbose_name="tournoi",
                                   related_name='matches', null=True, blank=True)
    players = models.ManyToManyField(Champion, verbose_name="participants",
                                     related_name='matches', through='MatchPlayer')
    ts = models.DateTimeField("date", default=timezone.now)
    options = models.CharField("options", max_length=500, default="{}")
    file_options = models.CharField("file_options", max_length=500, default="{}")

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
            map_id = int(self.file_options_dict.get('--map', '').split('/')[-1])
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


class MatchPlayer(ExportModelOperationsMixin('match_player'), models.Model):
    champion = models.ForeignKey(Champion, verbose_name="champion")
    match = models.ForeignKey(Match, verbose_name="match")
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
