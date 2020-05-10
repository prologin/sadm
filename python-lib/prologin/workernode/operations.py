# This file is part of Prologin-SADM.
#
# Copyright (c) 2013-2015 Antoine Pietri <antoine.pietri@prologin.org>
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
import gzip
import io
import os
import os.path
import tarfile
import tempfile
import textwrap
import yaml

from base64 import b64decode, b64encode
from camisole import isolate

ioloop = asyncio.get_event_loop()


def tar(path, compression='gz'):
    obj = io.BytesIO()
    with tarfile.open(fileobj=obj, mode='w:' + compression) as tar:
        tar.add(path)
    return obj.getvalue()


def untar(content, path, compression='gz'):
    obj = io.BytesIO(content)
    with tarfile.open(fileobj=obj, mode='r:' + compression) as tar:
        tar.extractall(path)


def get_output(isolate_result):
    return '\n'.join(
        (
            isolate_result.stdout.decode(errors='replace'),
            isolate_result.isolate_stdout.decode(errors='replace'),
        )
    )


def raise_isolate_error(message, cmd, isolator):
    output = textwrap.indent(
        isolator.stdout.decode('utf-8', errors='ignore'), prefix=' ' * 4
    )
    what = message
    what += "\n"
    what += "\nCommand: " + ' '.join(cmd)
    what += "\nOutput:\n" + output
    if isolator.isolate_stdout:
        what += "\nIsolate output:\n" + isolator.isolate_stdout.decode(
            errors='replace'
        )
    if isolator.isolate_stderr:
        what += "\nIsolate error:\n" + isolator.isolate_stderr.decode(
            errors='replace'
        )
    raise RuntimeError(what)


async def isolate_communicate(
    cmdline, limits=None, allowed_dirs=None, **kwargs
):
    isolator = isolate.Isolator(limits, allowed_dirs=allowed_dirs)
    async with isolator:
        await isolator.run(cmdline, **kwargs)
    return isolator


async def compile_champion(config, ctgz):
    """
    Compiles the champion contained in ctgz and returns a tuple TODO

    """
    ctgz = b64decode(ctgz)
    code_dir = os.path.abspath(os.path.dirname(__file__))
    compile_script = os.path.join(code_dir, 'compile-champion.sh')

    limits = {
        'wall-time': config['timeout'].get('compile', 400),
        'fsize': 50 * 1024,
    }
    allowed_dirs = ['/tmp:rw', code_dir, '/etc', config['path']['player_env']]

    isolator = isolate.Isolator(limits, allowed_dirs=allowed_dirs)
    async with isolator:
        compiled_path = isolator.path / 'champion-compiled.tar.gz'
        log_path = isolator.path / 'compilation.log'
        with (isolator.path / 'champion.tgz').open('wb') as f:
            f.write(ctgz)

        cmd = [compile_script, config['path']['player_env'], '/box']
        await isolator.run(cmd)
        ret = isolator.isolate_retcode == 0

        compilation_content = b''
        if ret:
            try:
                with compiled_path.open('rb') as f:
                    compilation_content = f.read()
            except FileNotFoundError:
                ret = False

        log = ''
        try:
            with log_path.open('r') as f:
                log = f.read()
        except FileNotFoundError:
            pass

    b64compiled = b64encode(compilation_content).decode()
    return ret, b64compiled, log


def isolator_compress(isolator, cmd, path):
    isolator_path = isolator.path / path
    try:
        with isolator_path.open('rb') as fd:
            return gzip.compress(fd.read())
    except PermissionError:
        raise_isolate_error(
            f"server: {path} does not have the correct permissions.\n",
            cmd,
            isolator,
        )
    except FileNotFoundError:
        raise_isolate_error(
            f"server: {path} was not created.\n", cmd, isolator
        )


async def spawn_server(
    config, rep_addr, pub_addr, nb_players, sockets_dir, map_contents
):
    # Build command
    # yapf: disable
    cmd = [
        config['path']['stechec_server'],
        "--rules", config['path']['rules'],
        "--rep_addr", rep_addr,
        "--pub_addr", pub_addr,
        "--nb_clients", str(nb_players),
        "--time", "3000",
        "--socket_timeout", "45000",
        "--dump", "/box/dump.json",
        "--replay", "/box/replay",
        # "--stats", "/box/stats.yaml",
        "--verbose", "1",
    ]
    # yapf: enable

    if map_contents is not None:
        f = tempfile.NamedTemporaryFile(mode='w')
        f.write(map_contents)
        f.flush()
        os.chmod(f.name, 0o644)
        cmd += ['--map', f.name]

    # Create the isolator
    limits = {'wall-time': config['timeout'].get('server', 400)}
    allowed_dirs = [
        '/var',
        '/etc',
        '/tmp',
        sockets_dir + ':rw',
        os.path.dirname(config['path']['stechec_server']),
        os.path.dirname(config['path']['rules']),
    ]
    isolator = isolate.Isolator(limits, allowed_dirs=allowed_dirs)
    async with isolator:
        # Run the isolated server
        await isolator.run(cmd, merge_outputs=True)

        # Retrieve the dump
        gzdump = isolator_compress(isolator, cmd, "dump.json")
        # Retrive the replay
        gzreplay = isolator_compress(isolator, cmd, "replay")
        # # Retrive the stats
        # gzstats = isolator_compress(isolator, cmd, "stats.yaml")
        gzstats = b''

    # Retrieve the output
    output = get_output(isolator)
    if isolator.isolate_retcode != 0:
        raise_isolate_error(
            "server: exited with a non-zero code", cmd, isolator
        )

    return output, gzdump, gzreplay, gzstats


async def spawn_client(
    config,
    req_addr,
    sub_addr,
    pl_id,
    champion_path,
    sockets_dir,
    map_contents,
    order_id=None,
):
    # Build environment
    env = {'CHAMPION_PATH': champion_path + '/', 'HOME': '/tmp'}

    # Build command
    # fmt: off
    cmd = [
        config['path']['stechec_client'],
        "--name", str(pl_id),
        "--rules", config['path']['rules'],
        "--champion", champion_path + '/champion.so',
        "--req_addr", req_addr,
        "--sub_addr", sub_addr,
        "--socket_timeout", "45000",
        "--time", "1500",
        "--verbose", "1",
    ]
    # fmt: on
    cmd += ["--client_id", str(order_id)] if order_id is not None else []

    if map_contents is not None:
        f = tempfile.NamedTemporaryFile(mode='w')
        f.write(map_contents)
        f.flush()
        os.chmod(f.name, 0o644)
        cmd += ['--map', f.name]

    # Build resource limits
    limits = {
        'wall-time': config['isolate'].get('time_limit_secs', 350),
        'mem': config['isolate'].get('mem_limit_MiB', 500) * 1000,
        'processes': config['isolate'].get('processes', 50),
        'fsize': 256,
    }
    allowed_dirs = [
        '/var',
        '/etc',
        '/tmp',
        sockets_dir + ':rw',
        champion_path,
        os.path.dirname(config['path']['stechec_client']),
        os.path.dirname(config['path']['rules']),
    ]

    # Remove memory limit if Java
    if os.path.exists(os.path.join(champion_path, 'Prologin.class')):
        limits.pop('mem')

    # Run the isolated client
    result = await isolate_communicate(
        cmd, limits, env=env, allowed_dirs=allowed_dirs, merge_outputs=True
    )
    return result.isolate_retcode, get_output(result)


# TODO: refactor return value to a dataclass
async def spawn_match(config, match_id, players, map_contents):
    # Build the domain sockets
    socket_dir = tempfile.TemporaryDirectory(prefix=f'workernode-{match_id}-')
    os.chmod(socket_dir.name, 0o777)
    f_reqrep = socket_dir.name + '/' + 'reqrep'
    f_pubsub = socket_dir.name + '/' + 'pubsub'
    s_reqrep = 'ipc://' + f_reqrep
    s_pubsub = 'ipc://' + f_pubsub

    # Server task
    task_server = asyncio.Task(
        spawn_server(
            config,
            s_reqrep,
            s_pubsub,
            len(players),
            socket_dir.name,
            map_contents,
        )
    )
    await asyncio.sleep(0.1)  # Let the server start

    # Retry every seconds for 5 seconds
    for i in range(5):
        if all(os.access(f, os.R_OK | os.W_OK) for f in (f_reqrep, f_pubsub)):
            break
        await asyncio.sleep(1)
    else:
        raise RuntimeError("Server socket was never created")

    # Players tasks
    tasks_players = {}
    champion_dirs = []

    # Sort by MatchPlayer id
    for oid, (pl_id, (c_id, ctgz)) in enumerate(sorted(players.items())):
        ctgz = b64decode(ctgz)
        cdir = tempfile.TemporaryDirectory()
        champion_dirs.append(cdir)
        untar(ctgz, cdir.name)
        tasks_players[pl_id] = asyncio.Task(
            spawn_client(
                config,
                s_reqrep,
                s_pubsub,
                pl_id,
                cdir.name,
                socket_dir.name,
                map_contents,
                order_id=oid,
            )
        )

    # Wait for the match to complete
    await asyncio.wait([task_server] + list(tasks_players.values()))

    # Get the output of the tasks
    server_out, dump, replay, stats = task_server.result()
    dump = b64encode(dump).decode()
    replay = b64encode(replay).decode()
    server_stats = b64encode(stats).decode()
    players_info = {
        pl_id: (
            players[pl_id][0],  # champion_id
            *t.result(),
        )  # retcode, output
        for pl_id, t in tasks_players.items()
    }

    # Extract the match result from the server stdout
    # stechec2 rules can output non-dict data, discard it
    server_yaml = server_out[server_out.find('---') :]
    server_result = yaml.safe_load_all(server_yaml)
    server_result = [r for r in server_result if isinstance(r, dict)]

    # Remove the champion temporary directories
    for tmpdir in champion_dirs:
        tmpdir.cleanup()
    socket_dir.cleanup()

    return server_result, server_out, dump, replay, server_stats, players_info
