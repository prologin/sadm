# SPDX-License-Identifier: GPL-2.0-or-later
import asyncio
import dataclasses
import logging
import datetime
import itertools
from collections import defaultdict, deque, Counter
import typing
from typing import (
    DefaultDict,
    Deque,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
)

from django.contrib.auth import get_user_model
from django.conf import settings as django_settings
from django.db.models import Max

import prologin.rpc.server
from prologin.concours.stechec.models import (
    Champion,
    Map,
    Match,
    MatchPlayer,
    MatchPriority,
    Tournament,
)

from prologin.matchmaker.monitoring import (
    matchmaker_queue_size,
    matchmaker_managed_champion_count,
    matchmaker_latest_champion_age_seconds,
    matchmaker_managed_match_count,
    matchmaker_insert_latency_seconds,
    matchmaker_scheduled_matches_total,
    matchmaker_cancelled_matches,
    matchmaker_match_limit_reached,
    matchmaker_new_champions_watch_latency_seconds,
    matchmaker_create_matches_latency_seconds,
)


@dataclasses.dataclass
class MatchItem:
    """Class that represents a MatchMaker match."""

    champions: Sequence[Champion]
    map: Optional[Map] = None
    cancelled: bool = False

    @classmethod
    def from_db(kls, match_item_db: Match) -> 'MatchItem':
        """Returns a MatchItem object from a Match model. """
        return kls(
            # Champions order is defined by the primary key of the ManyToMany
            # model.
            champions=tuple(
                player.champion
                for player in MatchPlayer.objects.filter(match=match_item_db)
                .order_by('pk')
                .all()
            ),
            map=match_item_db.map,
        )

    def __hash__(self):
        return hash((self.champions, self.map))

    def as_bulk_create(self, author, tournament: Tournament) -> Dict:
        return {
            'author': author,
            'tournament': tournament,
            'champions': self.champions,
            **({'map': self.map} if self.map else {}),
        }


class MatchMaker(prologin.rpc.server.BaseRPCApp):
    """The MatchMaker service."""

    def __init__(self, *args, config=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Service configuration
        self.config = config

        # Current champions
        self.champions: Set[Champion] = set()
        # Matches managed by MatchMaker
        self.matches_with_champion: DefaultDict[
            Champion, Set[MatchItem]
        ] = defaultdict(set)
        # The MatchMaker concours user
        self.author = None
        # The MatchMaker-managed tournament
        self.tournament: Tournament = None
        # Tournament maps
        self.maps: Sequence[Map] = []
        # The matches that are going to be scheduled
        self.next_matches: Deque[MatchItem] = deque()

        self._setup_monitoring()

    def _setup_monitoring(self) -> None:
        """Wires the monitoring probes."""
        matchmaker_queue_size.set_function(lambda: len(self.next_matches))
        matchmaker_managed_champion_count.set_function(
            lambda: len(self.champions)
        )
        matchmaker_latest_champion_age_seconds.set_function(
            lambda: (
                datetime.datetime.now()
                - max(
                    self.champions,
                    key=lambda elt: elt.ts,
                ).ts.date()
            ).total_seconds()
            if self.champions
            else 0
        )
        matchmaker_managed_match_count.set_function(
            lambda: sum(
                len(matches) for matches in self.matches_with_champion.values()
            )
        )
        matchmaker_match_limit_reached.set_function(self.match_limit_reached)

    def run(self, *args, **kwargs):
        logging.info(
            "matchmaker listening on port %s",
            self.config["matchmaker"]["port"],
        )

        # Start the service's main logic once the app is started
        self.app.on_startup.append(self.run_service)

        super().run(port=self.config["matchmaker"]["port"], *args, **kwargs)

    async def run_service(self, app):
        """Runs the service."""
        await self.setup()
        await self.bootstrap()

        # Start service components
        await asyncio.wait(
            [self.new_champions_watcher_loop(), self.create_matches_loop()]
        )

    def get_champions_query(self):
        """Returns a Django query selecting the champions in the tournament."""
        all_chs = Champion.objects.filter(status="ready", deleted=False)

        # TODO: move this configuration data to the Tournament model
        deadline_str = self.config["matchmaker"].get("deadline", None)
        include_staff = self.config["matchmaker"]["include_staff"]

        if deadline_str:
            deadline = datetime.datetime.fromisoformat(deadline_str)
            all_chs = all_chs.filter(ts__lte=deadline)
        if not include_staff:
            all_chs = all_chs.filter(author__is_staff=False)

        # Last champion of each user
        # https://stackoverflow.com/questions/16074498
        chs_ids = (
            all_chs.values("author__id")
            .annotate(max_id=Max("id"))
            .values("max_id")
        )

        return Champion.objects.filter(pk__in=chs_ids)

    async def setup(self) -> None:
        """Configures MatchMaker."""
        self.author, _ = get_user_model().objects.get_or_create(
            username=self.config["matchmaker"]["author_username"]
        )
        logging.info(
            "MatchMaker will use %s as author to schedule new matches",
            self.author,
        )

        self.tournament, _ = Tournament.objects.get_or_create(
            name=self.config["matchmaker"]["tournament_name"],
            defaults={"author": self.author},
        )
        logging.info(
            "MatchMaker will schedule matches for the %s tournament",
            self.tournament,
        )

        self.maps = list(self.tournament.maps.all())
        logging.info("MatchMaker will use the following maps: %s", self.maps)

    async def bootstrap(self) -> None:
        """Process backlog and set the service in a known state."""
        # Get latest champions
        latest_champions_query = self.get_champions_query()
        latest_champions = set(latest_champions_query)
        logging.info(
            "bootstrap: managing %d champions in the tournament",
            len(latest_champions),
        )

        # Remove champions that were the tournament but are not anymore
        old_champions = self.tournament.players.exclude(
            pk__in=latest_champions_query
        ).all()

        # Cancel matches by old champions
        await self.cancel_matches(old_champions)

        logging.info(
            "bootstrap: removing %d old champion(s) from the tournament: %s",
            old_champions.count(),
            list(old_champions),
        )
        self.tournament.players.remove(*old_champions)

        # Add new champions
        current_champions = self.tournament.players.all()
        new_champions = [
            c for c in latest_champions if c not in current_champions
        ]
        logging.info(
            "bootstrap: adding %d new champion(s) to the tournament: %s",
            len(new_champions),
            new_champions,
        )
        self.tournament.players.add(*new_champions)

        # Create missing matches
        logging.debug('bootstrap: computing missing matches')
        current_matches = (
            MatchItem.from_db(m)
            for m in self.tournament.matches.all().prefetch_related('players')
        )
        desired_matches: typing.Counter[MatchItem] = Counter(
            self.get_desired_matches(latest_champions)
        )
        desired_matches.subtract(current_matches)
        # Expand counter object to list of matches
        missing_matches = list(desired_matches.elements())
        logging.info(
            'bootstrap: making %d missing matches', len(missing_matches)
        )
        self.make_matches(missing_matches)

        self.champions = latest_champions

    def get_desired_matches(
        self, champions: Iterable[Champion]
    ) -> Iterator[MatchItem]:
        """Yields all expected matches for champions."""
        for chs in itertools.permutations(
            champions, r=django_settings.STECHEC_NPLAYERS
        ):
            yield from self.get_matches_with(chs)

    def get_matches_with(self, champions) -> Iterator[MatchItem]:
        """Yields all matches expected to be done between champions."""
        match = MatchItem(champions=champions)
        for r in range(self.config["matchmaker"].get("match_repeat", 1)):
            if django_settings.STECHEC_USE_MAPS:
                for map in self.maps:
                    yield dataclasses.replace(match, map=map)
            else:
                yield match

    def make_matches(self, matches) -> None:
        """Prepare matches for scheduling."""
        # Keep track of matches for each champion
        for match in matches:
            for champion in match.champions:
                self.matches_with_champion[champion].add(match)
        self.next_matches.extend(matches)

    async def cancel_matches(self, old_champions: Iterable[Champion]) -> None:
        """Cancel matches with old champions."""
        logging.info(
            'cancelling matches with old champions: %s', old_champions
        )

        # Cancel prepared matches
        for old_champion in old_champions:
            if old_champion not in self.matches_with_champion:
                continue
            for match in self.matches_with_champion.pop(old_champion):
                logging.info('cancelling %s', match)
                match.cancelled = True

        # Cancel already created matches
        cancelled_matches = self.tournament.matches.filter(
            players__in=old_champions
        )
        logging.info(
            'cancelling %d already created matches with old champions',
            len(cancelled_matches),
        )
        matchmaker_cancelled_matches.inc(len(cancelled_matches))
        cancelled_matches.filter(status='new').update(status='cancelled')
        for match in cancelled_matches.all():
            self.tournament.matches.remove(match)

    async def make_matches_for_champions(
        self, current_champions: Set[Champion], new_champions: Set[Champion]
    ) -> None:
        logging.info('scheduling matches for new champions: %s', new_champions)

        new_matches = []
        # Iterate over new matches
        for chs in itertools.permutations(
            new_champions | current_champions,
            r=django_settings.STECHEC_NPLAYERS,
        ):
            if not new_champions & set(chs):
                # No new champion in match
                continue

            new_matches.extend(self.get_matches_with(chs))

        self.make_matches(new_matches)

    async def new_champions_watch(self) -> None:
        """Watches the database for new champions and makes new matches."""
        # Query database
        latest_champions = set(self.get_champions_query())

        old_champions = self.champions - latest_champions
        if old_champions:
            await self.cancel_matches(old_champions)

        # Schedule new matches
        current_champions = self.champions & latest_champions
        new_champions = latest_champions - self.champions
        if new_champions:
            await self.make_matches_for_champions(
                current_champions, new_champions
            )

        # Commit set of current champions
        self.champions = latest_champions

    async def new_champions_watcher_loop(self) -> None:
        while True:
            with matchmaker_new_champions_watch_latency_seconds.time():
                await self.new_champions_watch()
            await asyncio.sleep(1)

    @matchmaker_insert_latency_seconds.time()
    def insert_matches(self, matches: Sequence[MatchItem]) -> None:
        """Insert new matches in the database."""
        logging.info('creating %d matches', len(matches))
        Match.launch_bulk(
            [
                new_match.as_bulk_create(self.author, self.tournament)
                for new_match in matches
            ],
            priority=MatchPriority.TOURNAMENT,
        )

    def match_limit_reached(self) -> bool:
        """Returns whether the limit of pending matches has been reached."""
        limit = self.config["matchmaker"]["match_pending_limit"]
        pending_matches = self.tournament.matches.filter(
            status__in=["new", "pending"]
        )
        return pending_matches.count() >= limit

    async def create_matches(self) -> None:
        """Create new matches at predefined batch size."""
        logging.info('%d matches in queue', len(self.next_matches))

        new_matches: List[MatchItem] = []
        while (
            len(new_matches) < self.config["matchmaker"]["match_batch_size"]
            and self.next_matches
            and not self.match_limit_reached()
        ):
            new_match = self.next_matches.popleft()
            if new_match.cancelled:
                logging.debug('skipping cancelled match: %s', new_match)
                continue
            new_matches.append(new_match)

        self.insert_matches(new_matches)

    async def create_matches_loop(self) -> None:
        while True:
            with matchmaker_create_matches_latency_seconds.time():
                await self.create_matches()
            await asyncio.sleep(1)
