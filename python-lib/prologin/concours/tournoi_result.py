#!/usr/bin/python

import django
import os
import sys
import time

if len(sys.argv) < 2:
    print('Usage: {} tournament_id'.format(sys.argv[0]))
    sys.exit(1)

os.environ['DJANGO_SETTINGS_MODULE'] = 'prologin.concours.settings'
django.setup()

from django.contrib.auth.models import User
from prologin.concours.stechec.models import Tournament, Match, MatchPlayer, Champion, TournamentPlayer, Map

tournoi = Tournament.objects.get(id=int(sys.argv[1]))
matches = Match.objects.filter(tournament=tournoi)

chs = []
for u in User.objects.all():
    ch = Champion.objects.filter(author=u, author__is_staff=False,
                                 deleted=False).order_by('-id')
    if len(ch) > 0:
        chs.append(ch[0])

def count_finished(matches):
    done = 0
    total = 0
    for m in matches:
        if m.status == 'done':
            done += 1
        total += 1
    return done, total

done, total = count_finished(matches)

if done < total:
    print('WARNING: This is a temporary result, some matches are not over yet.')
    print('Matchs done / launched: {} / {}'.format(done, total))

#matches = list(Match.objects.filter(createur = prologin, id__gt = 37911))

score = {}
indice = {}
for m in matches:
    c1, c2 = tuple(MatchPlayer.objects.filter(match=m))
    indice[c1.champion.id] = indice.get(c1.champion.id, 0) + c1.score
    indice[c2.champion.id] = indice.get(c2.champion.id, 0) + c2.score
    if c1.score > c2.score:
        score[c1.champion.id] = score.get(c1.champion.id, 0) + 2
    elif c2.score > c1.score:
        score[c2.champion.id] = score.get(c2.champion.id, 0) + 2
    else:
        score[c1.champion.id] = score.get(c1.champion.id, 0) + 1
        score[c2.champion.id] = score.get(c2.champion.id, 0) + 1

l = [(ch.author.username, score.get(ch.id, 0), indice.get(ch.id, 0), ch.id) for ch in chs]
l.sort(key=lambda x: x[2])
for e in l:
    print(e)

#print('Saving...')
#for (score, indice, id) in l:
#    ch = Champion.objects.get(pk=id)
#    p = TournamentPlayer(
#        champion = ch,
#        tournament = tournoi,
#        score = score
#    )
#    p.save()
