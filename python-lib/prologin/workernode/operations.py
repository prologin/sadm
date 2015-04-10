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
import errno
import fcntl
import gzip
import itertools
import logging
import os
import os.path
import subprocess
import sys
import tarfile
import tempfile
import time

from base64 import b64decode, b64encode

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
    res = []
    for l, content in file_opts.items():
        f = tempfile.NamedTemporaryFile()
        f.write(b64decode(content))
        res.append(l, f)
    return res


def gen_file_opts(files):
    return list(itertools.chain((att, f.name) for att, f in files.items()))


def gen_opts(opts):
    return list(itertools.chain(opts.items()))


@asyncio.coroutine
def communicate_forever(cmdline, data=None, env=None, max_len=None,
        truncate_message='', **kwargs):
    proc = yield from asyncio.create_subprocess_exec(*cmdline, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, **kwargs)

    # Send stdin
    if data:
        proc.stdin.write(data.encode())
        yield from proc.stdin.drain()
        proc.stdin.close()

    # Receive stdout
    stdout_buf = bytearray()
    while True:
        to_read = 4096
        if max_len is not None:
            to_read = min(to_read, max_len - len(stdout_buf))
            if not to_read:
                break
        chunk = yield from proc.stdout.read(to_read)
        if not chunk:
            break
        stdout_buf.extend(chunk)

    stdout = stdout_buf.decode()
    if not to_read:
        stdout += truncate_message

    exitcode = yield from proc.wait()
    return (exitcode, stdout)


@asyncio.coroutine
def communicate(cmdline, *args, timeout=None, **kwargs):
    return (yield from asyncio.wait_for(
        communicate_forever(cmdline, *args, **kwargs), timeout))


@asyncio.coroutine
def compile_champion(config, champion_path):
    """
    Compiles the champion at $champion_path/champion.tgz to
    $champion_path/champion-compiled.tar.gz

    Returns a tuple (ok, output), with ok = True/False and output being the
    output of the compilation script.
    """
    cmd = [config['path']['compile_script'], config['path']['makefiles'],
           champion_path]
    retcode, stdout = yield from communicate(cmd)
    return retcode == 0


@asyncio.coroutine
def spawn_server(config, rep_port, pub_port, nb_players, opts, file_opts):
    cmd = [config['path']['stechec_server'],
           "--rules", config['path']['rules'],
           "--rep_addr", "tcp://0.0.0.0:{}".format(rep_port),
           "--pub_addr", "tcp://0.0.0.0:{}".format(pub_port),
           "--nb_clients", str(nb_players + 1),
           "--time", "3000",
           "--socket_timeout", "45000",
           "--verbose", "1"]

    if opts is not None:
        cmd += gen_opts(opts)
    if file_opts is not None:
        files = create_file_opts(file_opts)
        fopts = gen_file_opts(files)
        cmd += fopts

    retcode, stdout = yield from communicate(cmd)
    if not (retcode == 0):
        logging.error(stdout.decode().strip())
        return ''

    return stdout.decode()


@asyncio.coroutine
def spawn_dumper(config, rep_port, pub_port, opts, file_opts):
    if 'dumper' not in config['path'] or not config['path']['dumper']:
        return

    if not os.path.exists(config['path']['dumper']):
        raise FileNotFoundError(config['path']['dumper'] + ' not found.')

    cmd = [config['path']['stechec_client'],
           "--name", "dumper",
           "--rules", config['path']['rules'],
           "--champion", config['path']['dumper'],
           "--req_addr", "tcp://127.0.0.1:{}".format(rep_port),
           "--sub_addr", "tcp://127.0.0.1:{}".format(pub_port),
           "--memory", "250000",
           "--time", "3000",
           "--socket_timeout", "45000",
           "--spectator",
           "--verbose", "1"]

    if opts is not None:
        cmd += gen_opts(opts)
    if file_opts is not None:
        files = create_file_opts(file_opts)
        fopts = gen_file_opts(files)
        cmd += fopts

    yield from asyncio.sleep(0.1) # Let the server start

    with tempfile.NamedTemporaryFile() as dump:
        new_env = os.environ.copy()
        new_env['DUMP_PATH'] = dump.name
        retcode, stdout = yield from communicate(cmd, env=new_env)
        gzdump = yield from ioloop.run_in_executor(None,
                gzip.compress, dump.read())
    return gzdump


@asyncio.coroutine
def spawn_client(config, ip, req_port, sub_port, pl_id, champion_path, opts,
                 file_opts=None):
    env = os.environ.copy()
    env['CHAMPION_PATH'] = champion_path + '/'

    cmd = [config['path']['stechec_client'],
                "--name", str(pl_id),
                "--rules", config['path']['rules'],
                "--champion", champion_path + '/champion.so',
                "--req_addr", "tcp://{ip}:{port}".format(ip=ip, port=req_port),
                "--sub_addr", "tcp://{ip}:{port}".format(ip=ip, port=sub_port),
                "--memory", "250000",
                "--socket_timeout", "45000",
                "--time", "1500",
                "--verbose", "1",
          ]

    if opts is not None:
        cmd += gen_opts(opts)
    if file_opts is not None:
        files = create_file_opts(file_opts)
        fopts = gen_file_opts(files)
        cmd += fopts

    retcode, stdout = yield from communicate(cmd, env, max_len=2 ** 18,
            truncate_message='\n\nLog truncated to stay below 256K.\n')
    return retcode, stdout.decode()
