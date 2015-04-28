#!/usr/bin/env python3

import argparse
import getpass
import psycopg
import prologin

get_matches = '''
SELECT
  stechec_match.id AS match_id,
  array_agg(stechec_champion.name) AS champion_names,
  array_agg(stechec_champion.id) AS champion_ids,
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
ORDER BY
  LEAST(stechec_matchplayer.score)
'''

match_done = set()

def write_matches_done():
    with open('matches_done', 'w') as f:
        f.write('\n'.join(str(i) for i in done))

def read_matches_done():
    s.clear()
    with open('matches_done') as f:
        for i in f.read().split('\n'):
            if i:
                match_done.add(int(i))

def get_matches(opts):
    conn = psycopg.connect(
            database=opts.database,
            user=opts.user,
            password=opts.password,
            host=opts.host,
            port=opts.port)
    cur = conn.cursor()
    cur.execute(get_matches)
    l = cur.fetchall()
    l = [(mid, list(zip(cnames, cids))) for cnames, cids, mid in l]
    return l


def get_replay(opts, match_id):
    return (requests.get('http://{}/{}/dump/'.format(
        opts.concours_url, match_id)).content)

if __name__ == '__main__':
    parser = argparse.ArgumentParser('SADM TV Mode')
    parser.add_argument('--concours-url', default='concours')
    parser.add_argument('--host', default='db')
    parser.add_argument('--port', type=int, default=5432)
    parser.add_argument('--database', default='concours')
    parser.add_argument('--user', default='concours')
    opts = parser.parse_args()
    opts.password = getpass.getpass('db password: ')

    while True:
        l = get_matches(opts)
        l = list(filter(lambda x: x not in match_done, l))
        i = random.randint(max(40, len(l)))
        launch_match(i)
