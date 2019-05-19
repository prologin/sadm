import itertools
import sys
from django.conf import settings
from django.core.management.base import BaseCommand

from prologin.concours.stechec.models import Match, Tournament


class Command(BaseCommand):
    help = "Launch a tournament in round-robin mode."

    def add_arguments(self, parser):
        parser.add_argument('--repeat', type=int, default=1,
                            help="Repeat each match this number of times")
        parser.add_argument('tournament_id', type=int)

    def handle(self, *args, **options):
        self.launch(options['tournament_id'], options['repeat'])

    def gen_matches(self, tournament, repeat=1):
        if settings.STECHEC_USE_MAPS and not tournament.maps.all():
            raise RuntimeError("Configured to run with maps but no maps "
                               "present in tournament.")

        matches = []
        for chs in itertools.product(tournament.players.all(),
                                     repeat=settings.STECHEC_NPLAYERS):
            # Don't fight against yourself
            ch_ids = [c.id for c in chs]
            if len(set(ch_ids)) != len(ch_ids):
                continue

            match = {'author': tournament.author,
                     'tournament': tournament,
                     'champions': chs}

            for r in range(repeat):
                if settings.STECHEC_USE_MAPS:
                    for map in tournament.maps.all():
                        matches.append({**match, 'map': map})
                else:
                    matches.append(match)

        return matches

    def launch(self, tournament_id, repeat=1):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            sys.exit("Tournament {} does not exist.".format(tournament_id))
        matches = self.gen_matches(tournament, repeat=repeat)

        print("You are about to schedule {} matchs for {} champions "
              "on {} maps.".format(len(matches), tournament.players.count(),
                                   tournament.maps.count()))
        confirm = input("Confirm? (yes/no) ")
        if confirm.lower() not in ("yes", "y"):
            sys.exit(1)

        Match.launch_bulk(matches)
