#!/usr/bin/python2

import django
import os
import sys
import time

os.environ['DJANGO_SETTINGS_MODULE'] = 'prologin.concours.settings'
django.setup()

from django.contrib.auth.models import User
from prologin.concours.stechec.models import Tournament, Match, MatchPlayer, Champion, TournamentPlayer, Map

prologin = User.objects.get(username="seirl")
tournoi = Tournament.objects.create()
maptournoi = Map.objects.get(pk=4)

def lancer_match(c1, c2):
    m = Match(author=prologin,
              tournament=tournoi)
    m.map = maptournoi.path
    MatchPlayer(champion=c1, match=m).save()
    MatchPlayer(champion=c2, match=m).save()
    m.status = 'new'
    m.save()
    return m.id

def all_finished(matches):
    for id in matches:
        m = Match.objects.get(pk=id)
        if m.status != 'done':
            return False
    return True

print('Fetching all competitors')
chs = []
for u in User.objects.all():
    ch = Champion.objects.filter(author=u, deleted=False).order_by('-id')
    if len(ch) > 0:
        chs.append(ch[0])

print('Done. Champions are :')
for ch in chs:
    print('-', ch)

print('Launching matches...')
matches = []
for c1 in chs:
    for c2 in chs:
        if c1.id == c2.id:
            continue
        print(c1.id, '-', c2.id)
        matches.append(lancer_match(c1, c2))

print('Waiting for matches to end...')
while not all_finished(matches):
    time.sleep(5)
    print('...')

print('Getting the matches...')
matches = [Match.objects.get(pk=id) for id in matches]

#matches = list(Match.objects.filter(createur = prologin, id__gt = 37911))

print('Calculating the scores...')
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

print('Sorting...')
l = [(score.get(ch.id, 0), indice.get(ch.id, 0), ch.id) for ch in chs]
l.sort()

print('Saving...')
for (score, indice, id) in l:
    ch = Champion.objects.get(pk=id)
    p = TournamentPlayer(
        champion = ch,
        tournament = tournoi,
        score = score
    )
    p.save()
