# SPDX-License-Identifier: GPL-2.0-or-later
import asyncio
import datetime
import itertools

from django.test import TestCase
from django.conf import settings
from django.contrib.auth import get_user_model

from prologin.concours.stechec.models import (
    Champion,
    Map,
    Match,
    MatchPriority,
    Tournament,
)

from .matchmaker import MatchItem, MatchMaker


class MatchMakerTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def expected_match_count_in_tournament(self):
        return (
            len(
                list(
                    itertools.permutations(
                        self._users, r=settings.STECHEC_NPLAYERS
                    )
                )
            )
            * self._mm_config['matchmaker']['match_repeat']
            * len(self._maps)
        )

    def assertMatchCountInTournament(self):
        self.assertEqual(
            self.expected_match_count_in_tournament(),
            self._mm_tournament.matches.count(),
            msg='Invalid number of matches in tournament.',
        )

    def assertTournamentValid(self):
        self.assertMatchCountInTournament()

        tournament_matches = self._mm_tournament.matches.all()
        for match in tournament_matches:
            self.assertEqual(match.status, 'new')
            self.assertEqual(match.priority, MatchPriority.TOURNAMENT)

        if self._mm_config['matchmaker']['match_repeat'] == 1:
            # All matches are unique
            matches_set = {
                MatchItem.from_db(match) for match in tournament_matches
            }
            self.assertEqual(len(matches_set), tournament_matches.count())

    def _update_champion(self, idx):
        old_champion = self._champions[idx]
        new_champion = Champion.objects.create(
            name='v2', author=old_champion.author, status='ready'
        )
        return old_champion, new_champion

    def setUp(self):
        self._user = get_user_model()

        # Create MatchMaker author
        self._mm_user = self._user.objects.create(username='MM test user')

        # Create tournament map
        test_map_count = 2
        self._maps = [
            Map.objects.create(name=f'MM test map {i}', author=self._mm_user)
            for i in range(test_map_count)
        ]

        # Create tournament
        self._mm_tournament = Tournament.objects.create(
            name='MM test tournament', author=self._mm_user
        )
        self._mm_tournament.maps.set(self._maps)

        # Create users
        test_user_count = 3
        self._users = [
            self._user.objects.create(username=str(i))
            for i in range(test_user_count)
        ]

        # Create champions
        self._champions = [
            Champion.objects.create(name=str(i), author=user, status='ready')
            for i, user in enumerate(self._users)
        ]

        # MatchMaker test config
        self._mm_config = {
            'matchmaker': {
                'tournament_name': self._mm_tournament.name,
                'match_batch_size': 100,
                'match_pending_limit': 100,
                'author_username': self._mm_user.username,
                'match_repeat': 1,
                'include_staff': False,
            }
        }

    def test_bootstrap_from_sratch(self):
        loop = asyncio.get_event_loop()

        async def task():
            mm = MatchMaker('matchmaker', config=self._mm_config)
            await mm.setup()
            await mm.bootstrap()
            await mm.create_matches()

        loop.run_until_complete(task())

        # All created matches are in the tournament
        for match in Match.objects.all():
            self.assertEqual(match.tournament, self._mm_tournament)

        self.assertTournamentValid()

    def test_boostrap_with_existing_matches(self):
        loop = asyncio.get_event_loop()

        async def task():
            mm = MatchMaker('matchmaker', config=self._mm_config)
            await mm.setup()
            await mm.bootstrap()
            await mm.create_matches()

        # First run
        loop.run_until_complete(task())

        # Create new champion
        old_champion, _ = self._update_champion(idx=0)

        # Boostrap again, with new champion
        loop.run_until_complete(task())

        for match in Match.objects.all():
            self.assertEqual(
                match.status == 'cancelled',
                old_champion in match.players.all(),
                'Match with old champion is not cancelled.',
            )
            self.assertEqual(
                match.tournament is None,
                old_champion in match.players.all(),
                'Match with old champion still in tournament.',
            )

        self.assertTournamentValid()

    def test_new_champions_watcher(self):
        loop = asyncio.get_event_loop()

        mm = MatchMaker('matchmaker', config=self._mm_config)

        async def task():
            await mm.setup()
            await mm.bootstrap()
            await mm.create_matches()

        loop.run_until_complete(task())

        # Create new champion
        _, new_champion = self._update_champion(idx=0)

        # Update MatchMaker state
        loop.run_until_complete(mm.new_champions_watch())

        self.assertGreater(
            len(mm.next_matches),
            0,
            "New matches were not created for new champion.",
        )
        # Next matches are with the new champion
        for match in mm.next_matches:
            self.assertIn(new_champion, match.champions)

        # Go ahead and create the new matches
        loop.run_until_complete(mm.create_matches())

        self.assertTournamentValid()

    def test_deadline_in_the_past(self):
        loop = asyncio.get_event_loop()

        yesterday_str = (
            datetime.datetime.now() - datetime.timedelta(days=1)
        ).isoformat()

        config = self._mm_config.copy()
        config['matchmaker']['deadline'] = yesterday_str
        mm = MatchMaker('matchmaker', config=config)

        async def task():
            await mm.setup()
            await mm.bootstrap()
            await mm.create_matches()

        loop.run_until_complete(task())

        self.assertEqual(
            self._mm_tournament.matches.count(),
            0,
            "Matches were created even though the deadline has passed.",
        )
