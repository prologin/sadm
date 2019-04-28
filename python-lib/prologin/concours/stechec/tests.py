import io
import shutil
import tarfile
from typing import BinaryIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from prologin.concours.stechec import models


class LoginMixin:
    def setUp(self):
        super().setUp()
        User = get_user_model().objects
        self.user_joseph = User.create_user('joseph', '', 'pswd')
        self.user_jeanne = User.create_user('jeanne', '', 'pswd')

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password='pswd'))


class StechecMixin:
    def setUp(self):
        super().setUp()
        settings.STECHEC_ROOT.mkdir(parents=True, exist_ok=False)

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(settings.STECHEC_ROOT)


class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def assertForbidden(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_new_champion(self):
        self.assertForbidden(self.client.get('/champions/new/'))

    def test_delete_champion(self):
        self.assertForbidden(self.client.get('/champions/1/delete/'))

    def test_source_champion(self):
        self.assertForbidden(self.client.get('/champions/1/sources/'))

    def test_my_matches(self):
        self.assertForbidden(self.client.get('/matches/mine/'))

    def test_new_matches(self):
        self.assertForbidden(self.client.get('/matches/new/'))


class ChampionTestCase(StechecMixin, LoginMixin, TestCase):
    champion_name = "Allez les bleus"

    def setUp(self):
        self.client = Client()
        super().setUp()
        self.login(self.user_joseph)

    def dummy_champion_tgz(self) -> BinaryIO:
        buf = io.BytesIO()
        with tarfile.open(mode='w:gz', fileobj=buf) as tar:

            def add_file(name, content):
                tarinfo = tarfile.TarInfo(name=name)
                tarinfo.size = len(content)
                tar.addfile(tarinfo, io.BytesIO(content))

            add_file("prologin.py", b"import this")
            add_file("_lang", b"python")

        buf.seek(0)
        return buf

    def test_upload_champion(self):
        r = self.client.get('/champions/new/')
        self.assertContains(r, "un champion")

        r = self.client.post(
            '/champions/new/', {
                'name': self.champion_name,
                'tarball': self.dummy_champion_tgz(),
                'comment': "On est tous ensemble"
            })
        self.assertRedirects(r, '/champions/1/')

        self.assertContains(self.client.get('/champions/all/'),
                            self.champion_name)
        self.assertContains(self.client.get('/champions/mine/', follow=True),
                            self.champion_name)

        r = self.client.get('/champions/1/')
        self.assertContains(r, self.user_joseph.username)
        self.assertContains(r, self.champion_name)
        self.assertContains(r, "On est tous ensemble")
        self.assertContains(r, "les sources")

    def test_delete_champion(self):
        self.test_upload_champion()

        r = self.client.post('/champions/1/delete/')
        self.assertRedirects(r, '/champions/mine/')

        self.assertNotContains(self.client.get('/champions/mine/'),
                               self.champion_name)

    def test_get_champion_sources(self):
        self.test_upload_champion()

        r = self.client.get('/champions/1/sources/', follow=True)
        self.assertTrue(r.has_header('Content-Encoding'))
        self.assertTrue(r.has_header('Content-Disposition'))
        self.assertIn('champion-1.tgz', r['Content-Disposition'])

        with tarfile.open(mode='r:gz', fileobj=io.BytesIO(r.content)) as tar:
            f = tar.extractfile('_lang')
            self.assertEqual(f.read(), b'python')

    def test_other_user_cannot_see_sources(self):
        self.test_upload_champion()

        self.login(self.user_jeanne)
        r = self.client.get('/champions/1/')
        self.assertContains(r, self.champion_name)
        self.assertNotContains(r, "les sources")

        r = self.client.get('/champions/1/sources/')
        self.assertEqual(r.status_code, 403)


class MapTestCase(StechecMixin, LoginMixin, TestCase):
    def setUp(self):
        self.client = Client()
        super().setUp()
        self.login(self.user_joseph)

    def test_add_map(self):
        r = self.client.get('/maps/new/')
        self.assertContains(r, "une carte")

        r = self.client.post('/maps/new/', {
            'name': "Such map",
            'contents': "Much contents, wow"
        })
        self.assertRedirects(r, '/maps/1/')

        r = self.client.get('/maps/all/')
        self.assertContains(r, self.user_joseph.username)
        self.assertContains(r, "Such map")

        r = self.client.get('/maps/1/')
        self.assertContains(r, self.user_joseph.username)
        self.assertContains(r, "Such map")
        self.assertContains(r, "Much contents")


class MatchTestCase(StechecMixin, LoginMixin, TestCase):
    def setUp(self):
        self.client = Client()
        super().setUp()
        self.login(self.user_joseph)

    def test_add_match(self):
        models.Champion.objects.create(name="bleu",
                                       author=self.user_joseph,
                                       status='ready')
        models.Champion.objects.create(name="rouge",
                                       author=self.user_jeanne,
                                       status='ready')
        models.Map.objects.create(name="Such map", author=self.user_joseph)

        r = self.client.get('/matches/new/')
        self.assertContains(r, "Such map")

        r = self.client.post('/matches/new/', {
            'champion_1': '1',
            'champion_2': '2',
            'map': '1'
        })
        self.assertEqual(models.Match.objects.count(), 1)
        self.assertRedirects(r, '/matches/1/')

        r = self.client.get('/matches/1/')
        self.assertContains(r, "bleu")
        self.assertContains(r, "rouge")
        self.assertContains(r, "Such map")
        self.assertContains(r, self.user_joseph.username)
        self.assertContains(r, self.user_jeanne.username)

    def test_match_no_dump(self):
        self.test_add_match()

        r = self.client.get('/matches/1/dump/')
        self.assertEqual(r.status_code, 404)

    def test_match_get_dump(self):
        self.test_add_match()
        models.Match.objects.update(status='done')
        match = models.Match.objects.get()
        match.dump_path.parent.mkdir(parents=True)
        with match.dump_path.open('wb') as dump:
            dump.write(b"dump tarball")

        r = self.client.get('/matches/1/dump/')
        self.assertEqual(r.content, b"dump tarball")

    def test_match_player_scores(self):
        self.test_add_match()

        models.Match.objects.update(status='done')
        p1, p2 = models.MatchPlayer.objects.all()
        p1.score = 42
        p2.score = 1337
        p1.save()
        p2.save()

        r = self.client.get('/matches/1/')
        self.assertContains(r, "42")
        self.assertContains(r, "1337")
