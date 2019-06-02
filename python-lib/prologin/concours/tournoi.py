#!/usr/bin/python

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

print('Launching tournament {}'.format(tournoi.id))

def lancer_match(c1, c2):
    m = Match(author=prologin,
              tournament=tournoi)
    m.status = 'new'
    m.save()
    MatchPlayer(champion=c1, match=m).save()
    MatchPlayer(champion=c2, match=m).save()
    return m.id

chs = []
for u in User.objects.all():
    ch = Champion.objects.filter(author=u, author__is_staff=False,
                                 deleted=False).order_by('-id')
    if len(ch) > 0:
        chs.append(ch[0])

print()
print('Champions are :')
for ch in chs:
    print('-', ch)

print()
print('Launching matches...')
for c1 in chs:
    for c2 in chs:
        for i in range(20):
            if c1.id == c2.id:
                continue
            print(c1.id, '-', c2.id)
            lancer_match(c1, c2)
