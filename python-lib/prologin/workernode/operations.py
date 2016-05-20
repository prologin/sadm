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
import itertools
import logging
import os
import os.path
import subprocess
import tarfile
import tempfile

from base64 import b64decode

from . import tools
from . import isolate

ioloop = asyncio.get_event_loop()

def tar(path, compression='gz'):
    with tempfile.NamedTemporaryFile() as temp:
        with tarfile.open(fileobj=temp, mode='w:' + compression) as tar:
            tar.add(path)
        temp.flush()
        temp.seek(0)
        return temp.read()


def untar(content, path, compression='gz'):
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(content)
        temp.seek(0)
        with tarfile.open(fileobj=temp, mode='r:' + compression) as tar:
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


async def compile_champion(config, champion_path):
    """
    Compiles the champion at $champion_path/champion.tgz to
    $champion_path/champion-compiled.tar.gz

    Returns a tuple (ok, output), with ok = True/False and output being the
    output of the compilation script.
    """
    code_dir = os.path.abspath(os.path.dirname(__file__))
    compile_script = os.path.join(code_dir, 'compile-champion.sh')
    cmd = [compile_script, config['path']['makefiles'], champion_path]
    retcode, _ = await tools.communicate(cmd)
    return retcode == 0


async def spawn_server(config, rep_addr, pub_addr, nb_players, opts, file_opts):
    dump = tempfile.NamedTemporaryFile()

    cmd = [config['path']['stechec_server'],
            "--rules", config['path']['rules'],
            "--rep_addr", rep_addr,
            "--pub_addr", pub_addr,
            "--nb_clients", str(nb_players),
            "--time", "3000",
            "--socket_timeout", "45000",
            "--verbose", "1",
            "--dump", dump.name]

    if opts is not None:
        cmd += opts
    if file_opts is not None:
        fopts, tmp_files = create_file_opts(file_opts)
        cmd.extend(fopts)

    try:
        retcode, stdout = await tools.communicate(cmd,
                coro_timeout=config['timeout'].get('server', 400))
    except asyncio.TimeoutError:
        logging.error("Server timeout")
        return "workernode: Server timeout", b''

    stdout = stdout.decode()
    gzdump = await ioloop.run_in_executor(None, gzip.compress, dump.read())

    if retcode != 0:
        logging.error(stdout.strip())
    return stdout, gzdump


async def spawn_client(config, req_addr, sub_addr, pl_id, champion_path, sockets_dir,
                 opts, file_opts=None, order_id=None):
    env = os.environ.copy()
    env['CHAMPION_PATH'] = champion_path + '/'

    # java fix for isolate (WTF)
    # see http://bugs.java.com/view_bug.do?bug_id=8043516
    env['MALLOC_ARENA_MAX'] = '1'

    cmd = [config['path']['stechec_client'],
                "--name", str(pl_id),
                "--rules", config['path']['rules'],
                "--champion", champion_path + '/champion.so',
                "--req_addr", req_addr,
                "--sub_addr", sub_addr,
                "--memory", "250000",
                "--socket_timeout", "45000",
                "--time", "1500",
                "--verbose", "1",
        ]
    cmd += ["--client_id", str(order_id)] if order_id is not None else []

    if opts is not None:
        cmd += opts
    if file_opts is not None:
        fopts, tmp_files = create_file_opts(file_opts)
        cmd.extend(fopts)

    try:
        retcode, stdout = await isolate.communicate(cmd, env=env,
                max_len=2 ** 18,
                truncate_message='\n\nLog truncated to stay below 256K.\n',
                coro_timeout=config['timeout'].get('client', 400),
                time_limit=config['isolate'].get('time_limit_secs', 350),
                mem_limit=config['isolate'].get('mem_limit_MiB', 500) * 1000,
                processes=config['isolate'].get('processes', 20),
                allowed_dirs=['/var', '/tmp', sockets_dir + ':rw'],
        )
        return retcode, stdout
    except asyncio.TimeoutError:
        logging.error("client timeout")
        return 1, b"workernode: Client timeout"
    except Exception as e:
        logging.exception(e)
        return 1, str(e).encode()
