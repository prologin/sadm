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
    with tempfile.NamedTemporaryFile('w', suffix='.c') as champion_path, \
         tempfile.NamedTemporaryFile('rb', suffix='.so') as compiled_path:
        champion_path.write(HELLO_SRC)
        champion_path.flush()
        subprocess.run(['gcc', '-shared', '-fPIE', champion_path.name,
                        '-o', compiled_path.name])
        return compiled_path.read()


def get_hello_compiled_tgz():
    compiled = get_hello_compiled_so()
    out = io.BytesIO()
    with tempfile.NamedTemporaryFile('wb') as compiled_path, \
         tarfile.open(fileobj=out, mode="w:gz") as tar:
        compiled_path.write(compiled)
        tar.add(compiled_path.name, arcname='champion.so')
    return b64encode(out.getvalue())


# Compilation tests

class CompilationTest(unittest.TestCase):
    def test_compile_simple(self):
        ctgz = get_hello_src_tgz()

        with tempfile.TemporaryDirectory() as makefiles:
            makefiles_p = pathlib.Path(makefiles)
            makefile = (makefiles_p / 'Makefile-cxx')
            with makefile.open('w') as mkf:
                mkf.write('''\
all: champion.so
champion.so: prologin.c
\tgcc -shared -fPIE prologin.c -o champion.so
list-run-reqs:
\t@echo champion.so
''')
            makefiles_p.chmod(0o755)
            makefile.chmod(0o644)
            config = {'path': {'makefiles': makefiles},
                      'timeout': {'compile': 400}}
            loop = asyncio.get_event_loop()
            ret, compiled, log = loop.run_until_complete(
                operations.compile_champion(config, ctgz))

        self.assertEqual(ret, True)
        for f in ('prologin.c', '_lang', 'champion.so'):
            self.assertIn(f, log)

        tgz = b64decode(compiled)
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

# Test additional opts
print('test_opt:', sys.argv[sys.argv.index('--test_opt') + 1])
fopt = sys.argv[sys.argv.index('--test_fopt') + 1]
assert os.access(fopt, os.R_OK)
print('test_fopt:', open(fopt).read())

# Write on all outputs
dump_path = sys.argv[sys.argv.index('--dump') + 1]
print('DUMP TEST', file=open(dump_path, 'w'))
print('some log on stderr', file=sys.stderr)

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

# Test additional opts
print('test_opt:', sys.argv[sys.argv.index('--test_opt') + 1])
fopt = sys.argv[sys.argv.index('--test_fopt') + 1]
assert os.access(fopt, os.R_OK)
print('test_fopt:', open(fopt).read())

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

        scripts = {'stechec_server': STECHEC_FAKE_SERVER.encode(),
                   'stechec_client': STECHEC_FAKE_CLIENT.encode(),
                   'rules': rules_so}
        with SetupScripts(scripts) as scripts_paths:
            config = get_worker_config(**scripts_paths)
            loop = asyncio.get_event_loop()

            # Construct map player_id -> [champion id, tarball]
            match_id = 4224
            players = {42: [0, ctgz], 1337: [0, ctgz]}
            opts = {'--test_opt': 'TEST_OPT'}
            f_opts = {'--test_fopt': b64encode(b'TEST_FOPT')}

            server_result, server_out, dump, players_info = (
                loop.run_until_complete(operations.spawn_match(
                    config, match_id, players, opts, f_opts)))

        self.assertEqual(gzip.decompress(b64decode(dump)), b'DUMP TEST\n')

        sr_expected = [{'player': 1, 'score': 42, 'nb_timeout': 0},
                       {'player': 2, 'score': 1337, 'nb_timeout': 0}]
        self.assertEqual(server_result, sr_expected)

        self.assertIn('test_opt: TEST_OPT', server_out)
        self.assertIn('test_fopt: TEST_FOPT', server_out)
        self.assertIn('some log on stderr', server_out)

        players_it = enumerate(sorted(players_info.items()), 1)
        for o_id, (pl_id, (_, retcode, output)) in players_it:
            self.assertEqual(retcode, 0,
                             msg='\nClient script output:\n' + output)
            self.assertIn('some log on stdout', output)
            self.assertIn('some log on stderr', output)
            self.assertIn('test_opt: TEST_OPT', output)
            self.assertIn('test_fopt: TEST_FOPT', output)
            self.assertIn('name: {}'.format(pl_id), output)
            self.assertIn('client_id: {}'.format(o_id), output)
