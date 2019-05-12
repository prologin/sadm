import collections
import sys
from django.core.management.base import BaseCommand

from prologin.concours.stechec.models import (Match, Tournament,
                                              TournamentPlayer)


class Command(BaseCommand):
    help = "Evaluate a tournament in round-robin mode."

    def add_arguments(self, parser):
        parser.add_argument(
            '--scoring',
            choices=['wins', 'cumulative'],
            default='wins',
            help=("The scoring mechanism. 'wins' only counts victories. "
                  "'cumulative' adds the final scores of each match."))
        parser.add_argument('tournament_id', type=int)

    def handle(self, *args, **options):
        tournament_id = options['tournament_id']
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            sys.exit("Tournament {} does not exist.".format(tournament_id))

        matches = Match.objects.filter(tournament=tournament)
        done = matches.filter(status='done').count()
        total = matches.count()

        if done < total:
            sys.exit("The tournament isn't over yet ({} matchs / {})."
                     .format(done, total))

        matches = tournament.matches.all().prefetch_related('players')

        score_wins = collections.defaultdict(int)
        score_cum = collections.defaultdict(int)

        for m in matches:
            # Cumulative scoring
            players = m.matchplayers.all()
            for player in players:
                score_cum[player.champion.id] += player.score

            # Wins scoring
            # One winner: +2 points for the winner, +0 for the losers
            # Ex-aequo, +1 point for each winner
            # XXX(seirl): I don't think this is a good way of scoring
            # tournaments of >2 player matches at all.
            max_score = max(p.score for p in players)
            winners = [p.champion.id for p in players if p.score == max_score]
            if len(winners) == 1:
                score_wins[winners[0]] += 2
            else:
                for winner in winners:
                    score_wins[winner] += 1

        players = tournament.tournamentplayers.all()
        for player in players:
            if options['scoring'] == 'wins':
                player.score = score_wins[player.champion.id]
            elif options['scoring'] == 'cumulative':
                player.score = score_cum[player.champion.id]
        TournamentPlayer.objects.bulk_update(players, ('score',))
