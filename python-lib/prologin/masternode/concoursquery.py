# -*- encoding: utf-8 -*-
# This file is part of Prologin-SADM.
#
# Copyright (c) 2014-2015 Antoine Pietri <antoine.pietri@prologin.org>
# Copyright (c) 2011 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2011-2014 Association Prologin <info@prologin.org>
#
# Prologin-SADM is free software: you can redistribute it AND/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prologin-SADM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prologin-SADM.  If not, see <http://www.gnu.org/licenses/>.

import aiopg
import psycopg2

REQUESTS = {
    'get_champions': '''
          SELECT
            stechec_champion.id AS id,
            auth_user.username AS name
          FROM
            stechec_champion
          LEFT JOIN auth_user
            ON auth_user.id = stechec_champion.author_id
          WHERE
            stechec_champion.status = %(champion_status)s
    ''',
    'set_champion_status': '''
          UPDATE
            stechec_champion
          SET
            status = %(champion_status)s
          WHERE
            stechec_champion.id = %(champion_id)s
    ''',
    'get_matches': '''
          SELECT
            stechec_match.id AS match_id,
            stechec_map.contents AS map_contents,
            array_agg(stechec_champion.id) AS champion_ids,
            array_agg(stechec_matchplayer.id) AS match_player_ids,
            array_agg(auth_user.username) AS user_names
          FROM
            stechec_match
          LEFT JOIN stechec_map
            ON stechec_match.map_id = stechec_map.id
          LEFT JOIN stechec_matchplayer
            ON stechec_matchplayer.match_id = stechec_match.id
          LEFT JOIN stechec_champion
            ON stechec_matchplayer.champion_id = stechec_champion.id
          LEFT JOIN auth_user
            ON stechec_champion.author_id = auth_user.id
          WHERE
            stechec_match.status = %(match_status)s
          GROUP BY
            stechec_match.id, stechec_map.id
          ORDER BY
            stechec_match.priority DESC
    ''',
    'set_match_status': '''
          UPDATE
            stechec_match
          SET
            status = %(match_status)s
          WHERE
            stechec_match.id = %(match_id)s
            AND status <> 'done'
    ''',
    'set_player_score': '''
          UPDATE
            stechec_matchplayer
          SET
            score = %(player_score)s,
            has_timeout = %(player_timeout)s
          WHERE
            stechec_matchplayer.id = %(player_id)s
    ''',
}


class ConcoursQuery:
    def __init__(self, config):
        self.host = config['sql']['host']
        self.port = config['sql']['port']
        self.user = config['sql']['user']
        self.password = config['sql']['password']
        self.database = config['sql']['database']
        self.pool = None

    async def connect(self):
        if self.pool is None:
            self.pool = await aiopg.create_pool(
                database=self.database,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                maxsize=64,
            )

    async def execute(self, name, params):
        if name not in REQUESTS:
            raise AttributeError('No such request')

        await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(REQUESTS[name], params)
                try:
                    res = await cursor.fetchall()
                except psycopg2.ProgrammingError:  # No results
                    return None
        return res

    async def executemany(self, name, seq_of_params):
        if name not in REQUESTS:
            raise AttributeError('No such request')

        await self.connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for p in seq_of_params:
                    await cursor.execute(REQUESTS[name], p)
