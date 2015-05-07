#!/usr/bin/env python3

import argparse
import getpass
import json
import psycopg2
import prologin
import random
import requests
import subprocess
import tempfile
import time

q_get_matches = '''
SELECT
  stechec_match.id AS match_id,
  array_agg(stechec_champion.name) AS champion_names,
  array_agg(stechec_matchplayer.id) as champion_ids,
  array_agg(stechec_matchplayer.score) as scores
FROM
  stechec_match
LEFT JOIN stechec_matchplayer
  ON stechec_matchplayer.match_id = stechec_match.id
LEFT JOIN stechec_champion
  ON stechec_matchplayer.champion_id = stechec_champion.id
WHERE
  stechec_match.status = 'done'
GROUP BY
  stechec_match.id,
  stechec_match.options
'''

#  stechec_matchplayer.score
#ORDER BY
#  LEAST(stechec_matchplayer.score)

match_done = set()

def write_matches_done():
    with open('matches_done', 'w') as f:
        f.write('\n'.join(str(i) for i in match_done))

def read_matches_done():
    match_done.clear()
    try:
        with open('matches_done') as f:
            for i in f.read().split('\n'):
                if i:
                    match_done.add(int(i))
    except FileNotFoundError:
        pass

def get_matches(opts):
    conn = psycopg2.connect(
            database=opts.database,
            user=opts.user,
            password=opts.password,
            host=opts.host,
            port=opts.port)
    cur = conn.cursor()
    cur.execute(q_get_matches)
    l = cur.fetchall()
    l = filter(lambda x: None not in x[2] and None not in x[3], l)
    l = sorted(l, key=lambda x: -min(x[3]))
    l = [(mid, list(zip(cnames, cids))) for mid, cnames, cids, scores in l]
    return l


def get_replay(opts, match_id):
    return (requests.get('http://{}/matches/{}/dump/'.format(
        opts.concours_url, match_id)).text)

def replay_match(opts, match_id, champions_list):
    trad = {str(cid): name for name, cid in champions_list}
    replay_content = get_replay(opts, match_id)
    replay_parts = []
    for i in replay_content.split('\n'):
        if i:
            c = json.loads(i)
            for i, p in c['players'].items():
                p['name'] = trad.get(p['name'], p['name'])
            c = json.dumps(c)
            replay_parts.append(c)
    replay_content = '\n'.join(replay_parts)
    with tempfile.NamedTemporaryFile() as f:
        f.write(replay_content.encode())
        f.flush()
        p = subprocess.Popen([opts.replay, '--tv-show', '--fullscreen', f.name])
        p.wait()

if __name__ == '__main__':
    parser = argparse.ArgumentParser('Match TV Mode')
    parser.add_argument('--concours-url', default='concours')
    parser.add_argument('--host', default='concours')
    parser.add_argument('--port', type=int, default=5432)
    parser.add_argument('--database', default='concours')
    parser.add_argument('--user', default='concours')
    parser.add_argument('--replay', default='/usr/bin/prologin2015-replay')
    opts = parser.parse_args()
    opts.password = getpass.getpass('db password: ')

    read_matches_done()
    while True:
        l = get_matches(opts)
        l = list(filter(lambda x: x[0] not in match_done, l))
        i = random.randint(0, min(40, len(l)))
        try:
            replay_match(opts, *l[i])
        except Exception as e:
            print('Error while replaying match {}: {}'.format(l[i][0], e))
        time.sleep(1)
        write_matches_done()
