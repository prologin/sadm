import asyncio
import collections
import ctypes
import gzip
import io
import os
import pathlib
import subprocess
import tarfile
import tempfile
import unittest
import yaml

from base64 import b64decode, b64encode

from prologin.workernode import operations

# Helpers to get 'hello world' dummy libs

HELLO_SRC = '''\
int hello() {
    return 42;
}'''


def put_file_in_tar(tar, name, content):
    content = content.encode()
    s = io.BytesIO(content)
    s.seek(0)
    tarinfo = tarfile.TarInfo(name=name)
    tarinfo.size = len(content)
    tar.addfile(tarinfo=tarinfo, fileobj=s)


def get_hello_src_tgz():
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        put_file_in_tar(tar, 'prologin.c', HELLO_SRC)
        put_file_in_tar(tar, '_lang', 'cxx')
    return b64encode(out.getvalue())


def get_hello_compiled_so():
    with tempfile.NamedTemporaryFile(
        'w', suffix='.c'
    ) as champion_path, tempfile.NamedTemporaryFile(
        'rb', suffix='.so'
    ) as compiled_path:
        champion_path.write(HELLO_SRC)
        champion_path.flush()
        subprocess.run(
            [
                'gcc',
                '-shared',
                '-fPIE',
                champion_path.name,
                '-o',
                compiled_path.name,
            ]
        )
        return compiled_path.read()


def get_hello_compiled_tgz():
    compiled = get_hello_compiled_so()
    out = io.BytesIO()
    with tempfile.NamedTemporaryFile('wb') as compiled_path, tarfile.open(
        fileobj=out, mode="w:gz"
    ) as tar:
        compiled_path.write(compiled)
        tar.add(compiled_path.name, arcname='champion.so')
    return b64encode(out.getvalue())


# Compilation tests


class CompilationTest(unittest.TestCase):
    def test_compile_simple(self):
        ctgz = get_hello_src_tgz()

        with tempfile.TemporaryDirectory() as makefiles:
            makefiles_p = pathlib.Path(makefiles)
            makefiles_cxx_p = makefiles_p / 'cxx'
            makefiles_cxx_p.mkdir()
            makefile = makefiles_cxx_p / 'Makefile-cxx'
            with makefile.open('w') as mkf:
                mkf.write(
                    '''\
all: champion.so
champion.so: prologin.c
\tgcc -shared -fPIE prologin.c -o champion.so
'''
                )
            makefiles_p.chmod(0o755)
            makefile.chmod(0o644)
            config = {
                'path': {'player_env': makefiles},
                'timeout': {'compile': 400},
            }
            result = asyncio.run(operations.compile_champion(config, ctgz))

        self.assertTrue(result['success'])
        for f in ('prologin.c', '_lang', 'champion.so'):
            self.assertIn(f, result['stdout'])

        tgz = b64decode(result['champion_compiled'])
        with tempfile.TemporaryDirectory() as tmpdir:
            operations.untar(tgz, tmpdir)
            cpath = os.path.join(tmpdir, 'champion.so')
            self.assertTrue(os.access(cpath, mode=os.R_OK))
            lib = ctypes.cdll.LoadLibrary(cpath)
            self.assertEqual(lib.hello(), 42)


# fake match test

STECHEC_FAKE_SERVER = '''\
#!/usr/bin/python3 -S
import os
import sys
import ctypes

# Test map
map = sys.argv[sys.argv.index('--map') + 1]
assert os.access(map, os.R_OK)
print('test_map:', open(map).read())

# Write on all outputs
dump_path = sys.argv[sys.argv.index('--dump') + 1]
replay_path = sys.argv[sys.argv.index('--replay') + 1]
stats_path = sys.argv[sys.argv.index('--stats') + 1]
print('some log on stderr', file=sys.stderr)
print('DUMP TEST', file=open(dump_path, 'w'))
print('REPLAY TEST', file=open(replay_path, 'w'))
print('STATS TEST', file=open(stats_path, 'w'))

# Test sockets
pubsub = sys.argv[sys.argv.index('--pub_addr') + 1][len('ipc://'):]
reqrep = sys.argv[sys.argv.index('--rep_addr') + 1][len('ipc://'):]
old_umask = os.umask(0)
open(pubsub, 'w').write('pubsub_server')
open(reqrep, 'w').write('reqrep_server')
os.umask(old_umask)

# Test libraries
rules = sys.argv[sys.argv.index('--rules') + 1]
assert os.access(rules, os.R_OK | os.X_OK)
assert ctypes.cdll.LoadLibrary(rules).hello() == 42

# Write score
print("""
---
player: 1
score: 42
nb_timeout: 0
---
player: 2
score: 1337
nb_timeout: 0""")
'''

STECHEC_FAKE_CLIENT = '''\
#!/usr/bin/python3 -S
import os
import sys
import ctypes

# Test args
print('name:', sys.argv[sys.argv.index('--name') + 1])
print('client_id:', sys.argv[sys.argv.index('--client_id') + 1])

# Test map
map = sys.argv[sys.argv.index('--map') + 1]
assert os.access(map, os.R_OK)
print('test_map:', open(map).read())

# Write on all outputs
print('some log on stdout')
print('some log on stderr', file=sys.stderr)

# Test sockets
pubsub = sys.argv[sys.argv.index('--sub_addr') + 1][len('ipc://'):]
reqrep = sys.argv[sys.argv.index('--req_addr') + 1][len('ipc://'):]
assert os.access(pubsub, os.R_OK | os.W_OK)
assert os.access(reqrep, os.R_OK | os.W_OK)
assert open(pubsub).read() == 'pubsub_server'
assert open(reqrep).read() == 'reqrep_server'

# Test libraries
rules = sys.argv[sys.argv.index('--rules') + 1]
champion = sys.argv[sys.argv.index('--champion') + 1]

assert os.access(rules, os.R_OK | os.X_OK)
assert ctypes.cdll.LoadLibrary(rules).hello() == 42

assert os.access(rules, os.R_OK | os.X_OK)
assert ctypes.cdll.LoadLibrary(rules).hello() == 42
'''


def get_worker_config(**kwargs):
    d = collections.defaultdict(str)
    d.update(kwargs)
    worker_config = '''
    path:
        stechec_server: {stechec_server}
        stechec_client: {stechec_client}
        rules: {rules}
    timeout:
        server: 500
    isolate:
        time_limit_secs: 350
    '''
    return yaml.safe_load(worker_config.format(**d))


class SetupScripts:
    def __init__(self, scripts):
        self.scripts = scripts
        self.temp_list = []

    def __enter__(self):
        res = {}
        for name, content in self.scripts.items():
            f = tempfile.NamedTemporaryFile('wb+', delete=False)
            with f as fd:
                fd.write(content)
            os.chmod(f.name, 0o755)
            res[name] = f.name
            self.temp_list.append(f.name)
        return res

    def __exit__(self, exc, value, tb):
        for tmp in self.temp_list:
            os.unlink(tmp)


class FakeMatchTest(unittest.TestCase):
    def test_spawn_match_simple(self):
        rules_so = get_hello_compiled_so()
        ctgz = get_hello_compiled_tgz()

        scripts = {
            'stechec_server': STECHEC_FAKE_SERVER.encode(),
            'stechec_client': STECHEC_FAKE_CLIENT.encode(),
            'rules': rules_so,
        }
        with SetupScripts(scripts) as scripts_paths:
            config = get_worker_config(**scripts_paths)

            # Construct map player_id -> [champion id, tarball]
            players = {42: [0, ctgz], 1337: [0, ctgz]}
            map_contents = 'TEST_MAP'

            result = asyncio.run(
                operations.spawn_match(config, players, map_contents)
            )

        self.assertEqual(
            gzip.decompress(b64decode(result['dump'])), b'DUMP TEST\n'
        )
        self.assertEqual(
            gzip.decompress(b64decode(result['replay'])), b'REPLAY TEST\n'
        )
        self.assertEqual(
            gzip.decompress(b64decode(result['stats'])), b'STATS TEST\n'
        )

        sr_expected = [
            {'player': 1, 'score': 42, 'nb_timeout': 0},
            {'player': 2, 'score': 1337, 'nb_timeout': 0},
        ]
        self.assertEqual(result['match_result'], sr_expected)

        self.assertIn('map: TEST_MAP', result['stdout'])
        self.assertIn('some log on stderr', result['stderr'])

        players_it = enumerate(sorted(result['players'].items()))
        for order_id, (player_id, player_result) in players_it:
            self.assertEqual(
                player_result['success'],
                True,
                msg='\nClient script output:\n' + player_result['stdout'],
            )
            self.assertIn('some log on stdout', player_result['stdout'])
            # stderr is merged in stdout
            self.assertIn('some log on stderr', player_result['stdout'])
            self.assertIn('map: TEST_MAP', player_result['stdout'])
            self.assertIn(f'name: {player_id}', player_result['stdout'])
            self.assertIn(f'client_id: {order_id}', player_result['stdout'])
