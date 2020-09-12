# This file is part of Prologin-SADM.
#
# Copyright (c) 2013-2020 Antoine Pietri <antoine.pietri@prologin.org>
# Copyright (c) 2011 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2011-2014 Association Prologin <info@prologin.org>
#
# Prologin-SADM is free software: you can redistribute it and/or modify
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

import asyncio
import contextlib
import gzip
import io
import logging
import os
import os.path
import tarfile
import tempfile
import traceback
from typing import Dict, List, Any

import yaml

from base64 import b64decode, b64encode
from camisole import isolate
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_fixed


def tar(path: os.PathLike, compression: str = 'gz') -> bytes:
    """
    Create a tarball of the given path.

    Args:
        path: the directory to tarball
        compression: the tarball compression format

    Returns:
        the binary representation of the tarball object.
    """
    obj = io.BytesIO()
    with tarfile.open(fileobj=obj, mode='w:' + compression) as tarobj:
        tarobj.add(str(path))
    return obj.getvalue()


def untar(content: bytes, path: os.PathLike, compression: str = 'gz'):
    """
    Extract a tarball at a given path.

    Args:
        content: the binary representation of the tarball.
        path: the path of the extracted directory
        compression: the tarball compression format
    """
    obj = io.BytesIO(content)
    with tarfile.open(fileobj=obj, mode='r:' + compression) as tarobj:
        tarobj.extractall(path)


def read_compress_b64(path: Path) -> str:
    """
    Read the given file, gzip compress it and return a base64 of the result.
    """
    return b64encode(gzip.compress(path.read_bytes())).decode()


class Operation:
    def __init__(self, config):
        self.config = config
        self.isolator = None
        self.isolate_limits: Dict[str, Any] = {}
        self.isolate_allowed_dirs: List[str] = []
        self.result: Dict[str, Any] = {
            'success': None,
            'isolate': {},
            'stdout': None,
            'stderr': None,
        }

    @contextlib.asynccontextmanager
    async def spawn_isolator(self):
        isolator = isolate.Isolator(
            self.isolate_limits, allowed_dirs=self.isolate_allowed_dirs
        )
        async with isolator:
            self.isolator = isolator
            try:
                yield isolator
            finally:
                self.result['success'] = isolator.isolate_retcode == 0
                if isolator.stdout is not None:
                    self.result['stdout'] = isolator.stdout.decode(
                        errors='replace'
                    )
                if isolator.stderr is not None:
                    self.result['stderr'] = isolator.stderr.decode(
                        errors='replace'
                    )
                if self.isolator.isolate_stdout is not None:
                    self.result['isolate'][
                        'stdout'
                    ] = isolator.isolate_stdout.decode(errors='replace')
                if self.isolator.isolate_stderr is not None:
                    self.result['isolate'][
                        'stderr'
                    ] = isolator.isolate_stderr.decode(errors='replace')
                self.isolator = None

    async def __call__(self, *args, **kwargs):
        try:
            async with self.spawn_isolator():
                await self._run(*args, **kwargs)
        except Exception as e:
            logging.exception('Workernode operation error:')
            self.result['success'] = False
            self.result['error'] = str(e)
            self.result['traceback'] = traceback.format_exc()
        return self.result

    async def _run(self, *args, **kwargs):
        raise NotImplemented

    # Shared utilities

    def write_map(self, map_content):
        if map_content is not None:
            map_file = self.isolator.path / 'map.txt'
            map_file.write_text(map_content)
            map_file.chmod(0o644)
            return Path('/box/map.txt')


class CompileChampion(Operation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = {
            'champion_compiled': None,
            **self.result,
        }
        self.limits = {
            'wall-time': self.config['timeout'].get('compile', 400),
            'fsize': 50 * 1024,
        }
        self.isolate_allowed_dirs = [
            '/tmp:rw',
            '/etc',
            self.config['path']['player_env'],
        ]

    def write_champion(self, champion_tgz_b64: str):
        ctgz = b64decode(champion_tgz_b64)
        (self.isolator.path / 'champion.tgz').write_bytes(ctgz)
        return Path('/box')

    def write_compile_script(self):
        compile_script_path = Path(__file__).parent / 'compile-champion.sh'
        compile_script = compile_script_path.read_text()
        compile_script_path = self.isolator.path / 'compile-champion.sh'
        compile_script_path.write_text(compile_script)
        compile_script_path.chmod(0o755)
        return Path('/box/compile-champion.sh')

    def read_champion_compiled(self):
        compiled_path = self.isolator.path / 'champion-compiled.tar.gz'
        self.result['champion_compiled'] = b64encode(
            compiled_path.read_bytes()
        ).decode()

    async def _run(self, *, champion_tgz_b64: str):
        compile_script = self.write_compile_script()
        champion_path = self.write_champion(champion_tgz_b64)

        cmd: List[str] = [
            str(compile_script),
            self.config['path']['player_env'],
            str(champion_path),
        ]
        await self.isolator.run(cmd, merge_outputs=True)

        self.read_champion_compiled()


class SpawnServer(Operation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = {
            'dump': None,
            'replay': None,
            'stats': None,
            'match_result': None,
            **self.result,
        }
        self.limits = {'wall-time': self.config['timeout'].get('server', 400)}
        self.isolate_allowed_dirs = [
            '/var',
            '/etc',
            '/tmp',
            os.path.dirname(self.config['path']['stechec_server']),
            os.path.dirname(self.config['path']['rules']),
        ]

    async def _run(
        self,
        *,
        sockets_dir: os.PathLike,
        rep_addr: str,
        pub_addr: str,
        nb_players: int,
        map_content: str,
    ):
        self.isolate_allowed_dirs.append(str(sockets_dir) + ':rw')
        # fmt: off
        cmd = [
            self.config['path']['stechec_server'],
            "--rules", self.config['path']['rules'],
            "--rep_addr", rep_addr,
            "--pub_addr", pub_addr,
            "--nb_clients", str(nb_players),
            "--time", "3000",
            "--socket_timeout", "45000",
            "--dump", "/box/dump.json",
            "--replay", "/box/replay",
            "--stats", "/box/stats.yaml",
            "--verbose", "1",
        ]
        # fmt: on

        if map_path := self.write_map(map_content):
            cmd += ['--map', str(map_path)]

        await self.isolator.run(cmd)
        if self.isolator.isolate_retcode != 0:
            raise RuntimeError(
                "server: exited with a non-zero code ({}).".format(
                    self.isolator.isolate_retcode
                )
            )
        self.result['dump'] = read_compress_b64(
            self.isolator.path / 'dump.json'
        )
        self.result['replay'] = read_compress_b64(
            self.isolator.path / "replay"
        )
        self.result['stats'] = read_compress_b64(
            self.isolator.path / "stats.yaml"
        )


class SpawnClient(Operation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = {
            'champion_id': None,
            **self.result,
        }
        self.limits = {
            'wall-time': self.config['isolate'].get('time_limit_secs', 350),
            'mem': self.config['isolate'].get('mem_limit_MiB', 500) * 1000,
            'processes': self.config['isolate'].get('processes', 50),
            'fsize': 256,
        }
        self.isolate_allowed_dirs = [
            '/var',
            '/etc',
            '/tmp',
            os.path.dirname(self.config['path']['stechec_client']),
            os.path.dirname(self.config['path']['rules']),
        ]

    def extract_champion(self, champion_tgz_b64: str) -> Path:
        ctgz: bytes = b64decode(champion_tgz_b64)
        untar(ctgz, self.isolator.path)
        return Path('/box')

    async def _run(
        self,
        *,
        sockets_dir: os.PathLike,
        req_addr: str,
        sub_addr: str,
        champion_id: int,
        player_id: int,
        champion_tgz_b64: str,
        map_content: str = None,
        order_id: int = None,
    ):
        self.result['champion_id'] = champion_id

        self.isolate_allowed_dirs.append(str(sockets_dir) + ':rw')

        champion_path = self.extract_champion(champion_tgz_b64)
        env: Dict[str, str] = {
            'CHAMPION_PATH': str(champion_path),
            'HOME': '/tmp',
        }

        # fmt: off
        cmd: List[str] = [
            self.config['path']['stechec_client'],
            "--name", str(player_id),
            "--rules", self.config['path']['rules'],
            "--champion", str(champion_path / 'champion.so'),
            "--req_addr", req_addr,
            "--sub_addr", sub_addr,
            "--socket_timeout", "45000",
            "--time", "1500",
            "--verbose", "1",
        ]
        # fmt: on
        if order_id is not None:
            cmd += ["--client_id", str(order_id)]
        if map_path := self.write_map(map_content):
            cmd += ['--map', str(map_path)]

        # Run the isolated client
        await self.isolator.run(cmd, env=env, merge_outputs=True)


async def compile_champion(config, champion_tgz_b64):
    compile_champion = CompileChampion(config)
    return await compile_champion(champion_tgz_b64=champion_tgz_b64)


async def spawn_match(config, players, map_content):
    # Build the domain sockets
    socket_dir = tempfile.TemporaryDirectory(prefix='workernode-match-')
    os.chmod(socket_dir.name, 0o777)
    f_reqrep = socket_dir.name + '/' + 'reqrep'
    f_pubsub = socket_dir.name + '/' + 'pubsub'
    s_reqrep = 'ipc://' + f_reqrep
    s_pubsub = 'ipc://' + f_pubsub

    # Server task
    spawn_server = SpawnServer(config)
    task_server = asyncio.create_task(
        spawn_server(
            sockets_dir=socket_dir.name,
            rep_addr=s_reqrep,
            pub_addr=s_pubsub,
            nb_players=len(players),
            map_content=map_content,
        )
    )
    await asyncio.sleep(0.1)  # Let the server start

    @retry(reraise=True, stop=stop_after_attempt(7), wait=wait_fixed(2))
    async def wait_for_server_sockets():
        if not all(
            os.access(f, os.R_OK | os.W_OK) for f in (f_reqrep, f_pubsub)
        ):
            raise RuntimeError("Server socket was not created")

    await wait_for_server_sockets()

    # Players tasks
    tasks_players = {}

    player_iter = sorted(players.items())  # Sort by MatchPlayer id
    for order_id, (player_id, (champion_id, ctgz)) in enumerate(player_iter):
        spawn_client = SpawnClient(config)
        task_client = asyncio.create_task(
            spawn_client(
                sockets_dir=socket_dir.name,
                req_addr=s_reqrep,
                sub_addr=s_pubsub,
                champion_id=champion_id,
                player_id=player_id,
                champion_tgz_b64=ctgz,
                map_content=map_content,
                order_id=order_id,
            )
        )
        tasks_players[player_id] = task_client

    # Wait for the match to complete
    await asyncio.wait([task_server] + list(tasks_players.values()))

    # Get the output of the tasks
    result = task_server.result()
    result['players'] = {
        player_id: t.result() for player_id, t in tasks_players.items()
    }

    # Extract the match result from the server stdout
    # stechec2 rules can output non-dict data, discard it
    server_yaml = result['stdout'][result['stdout'].find('---') :]
    server_result = yaml.safe_load_all(server_yaml)
    result['match_result'] = [r for r in server_result if isinstance(r, dict)]

    return result
