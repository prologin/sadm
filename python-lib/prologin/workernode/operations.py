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
import itertools
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


def create_file_opts(file_opts):
    opts = []
    files = []
    for l, content in file_opts.items():
        f = tempfile.NamedTemporaryFile()
        f.write(b64decode(content))
        f.flush()
        os.chmod(f.name, 0o644)
        opts.append(l)
        opts.append(f.name)
        files.append(f)
    return opts, files


def get_output(isolate_result):
    return '\n'.join((isolate_result.stdout,
                      isolate_result.isolate_stdout.decode()))


def raise_isolate_error(message, cmd, isolator):
    output = textwrap.indent(isolator.stdout, prefix=' ' * 4)
    raise RuntimeError(message
                       + "\n\nCommand: " + ' '.join(cmd)
                       + "\nOutput:\n" + output)


async def isolate_communicate(cmdline, limits=None, allowed_dirs=None,
                              **kwargs):
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

    limits = {'wall-time': config['timeout'].get('compile', 400),
              'fsize': 50 * 1024}
    allowed_dirs = ['/tmp:rw', code_dir, '/etc']

    isolator = isolate.Isolator(limits, allowed_dirs=allowed_dirs)
    async with isolator:
        compiled_path = isolator.path / 'champion-compiled.tar.gz'
        log_path = isolator.path / 'compilation.log'
        with (isolator.path / 'champion.tgz').open('wb') as f:
            f.write(ctgz)

        cmd = [compile_script, config['path']['makefiles'], '/box']
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


async def spawn_server(config, rep_addr, pub_addr, nb_players, sockets_dir,
                       opts, file_opts):
    # Build command
    cmd = [config['path']['stechec_server'],
           "--rules", config['path']['rules'],
           "--rep_addr", rep_addr,
           "--pub_addr", pub_addr,
           "--nb_clients", str(nb_players),
           "--time", "3000",
           "--socket_timeout", "45000",
           "--dump", "/box/dump.json",
           "--verbose", "1"]

    if opts is not None:
        cmd += opts
    if file_opts is not None:
        fopts, tmp_files = create_file_opts(file_opts)
        cmd.extend(fopts)

    # Create the isolator
    limits = {'wall-time': config['timeout'].get('server', 400)}
    isolator = isolate.Isolator(
        limits, allowed_dirs=['/var', '/tmp', sockets_dir + ':rw'])
    async with isolator:
        # Run the isolated server
        await isolator.run(cmd, merge_outputs=True)

        # Retrieve the dump and gz-compress it
        try:
            dump_path = isolator.path / 'dump.json'
            with dump_path.open('rb') as dump:
                gzdump = gzip.compress(dump.read())
        except FileNotFoundError:
            raise_isolate_error("server: dump.json was not created.\n", cmd,
                                isolator)

    # Retrieve the output
    output = get_output(isolator)
    if isolator.isolate_retcode != 0:
        raise_isolate_error("server: exited with a non-zero code", cmd,
                            isolator)
    return output, gzdump


async def spawn_client(config, req_addr, sub_addr, pl_id, champion_path,
                       sockets_dir, opts, file_opts=None, order_id=None):
    # Build environment
    env = os.environ.copy()
    env['CHAMPION_PATH'] = champion_path + '/'

    # FIXME: JAVA SHOULD NOT BE MEMORY-ISOLATED
    # java fix for isolate (WTF)
    # see http://bugs.java.com/view_bug.do?bug_id=8043516
    env['MALLOC_ARENA_MAX'] = '1'

    # Build command
    cmd = [config['path']['stechec_client'],
           "--name", str(pl_id),
           "--rules", config['path']['rules'],
           "--champion", champion_path + '/champion.so',
           "--req_addr", req_addr,
           "--sub_addr", sub_addr,
           "--memory", "250000",
           "--socket_timeout", "45000",
           "--time", "1500",
           "--verbose", "1"]
    cmd += ["--client_id", str(order_id)] if order_id is not None else []

    if opts is not None:
        cmd += opts
    if file_opts is not None:
        fopts, tmp_files = create_file_opts(file_opts)
        cmd.extend(fopts)

    # Build resource limits
    limits = {
        'wall-time': config['isolate'].get('time_limit_secs', 350),
        'mem': config['isolate'].get('mem_limit_MiB', 500) * 1000,
        'processes': config['isolate'].get('processes', 50),
        'fsize': 256,
    }

    # Run the isolated client
    result = await isolate_communicate(
        cmd, limits, env=env,
        allowed_dirs=['/var', '/tmp', sockets_dir + ':rw'],
        merge_outputs=True
    )
    return result.isolate_retcode, get_output(result)


async def spawn_match(config, players, opts=None, file_opts=None):
    # Build the domain sockets
    socket_dir = tempfile.TemporaryDirectory(prefix='workernode-')
    os.chmod(socket_dir.name, 0o777)
    f_reqrep = socket_dir.name + '/' + 'reqrep'
    f_pubsub = socket_dir.name + '/' + 'pubsub'
    s_reqrep = 'ipc://' + f_reqrep
    s_pubsub = 'ipc://' + f_pubsub

    opts = list(itertools.chain(*opts.items()))

    # Server task
    task_server = asyncio.Task(
        spawn_server(config, s_reqrep, s_pubsub, len(players), socket_dir.name,
                     opts, file_opts))
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
    for oid, (pl_id, (c_id, ctgz)) in enumerate(sorted(players.items()), 1):
        ctgz = b64decode(ctgz)
        cdir = tempfile.TemporaryDirectory()
        champion_dirs.append(cdir)
        untar(ctgz, cdir.name)
        tasks_players[pl_id] = asyncio.Task(spawn_client(
            config, s_reqrep, s_pubsub, pl_id, cdir.name,
            socket_dir.name, opts, file_opts, order_id=oid))

    # Wait for the match to complete
    await asyncio.wait([task_server] + list(tasks_players.values()))

    # Get the output of the tasks
    server_out, dump = task_server.result()
    dump = b64encode(dump).decode()
    players_info = {pl_id: (players[pl_id][0],  # champion_id
                            *t.result())  # retcode, output
                    for pl_id, t in tasks_players.items()}

    # Extract the match result from the server stdout
    # stechec2 rules can output non-dict data, discard it
    server_yaml = server_out[server_out.find('---'):]
    server_result = yaml.safe_load_all(server_yaml)
    server_result = [r for r in server_result if isinstance(r, dict)]

    # Remove the champion temporary directories
    for tmpdir in champion_dirs:
        tmpdir.cleanup()
    socket_dir.cleanup()

    return server_result, server_out, dump, players_info
