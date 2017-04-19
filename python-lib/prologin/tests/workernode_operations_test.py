import asyncio
import collections
import ctypes
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


def get_hello_compiled_tgz():
    with tempfile.NamedTemporaryFile() as champion_path, \
         tempfile.NamedTemporaryFile() as compiled_path:
        open(champion_path.name, 'w').write(HELLO_SRC)
        subprocess.run(['gcc', '-shared', '-fPIE', champion_path.name,
                        '-o', compiled_path.name])
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode="w:gz") as tar:
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
            makefiles_p.chmod(755)
            makefile.chmod(644)
            config = {'path': {'makefiles': makefiles},
                      'timeout': {'compile': 400}}
            loop = asyncio.get_event_loop()
            ret, compiled, log, info = loop.run_until_complete(
                operations.compile_champion(config, ctgz))

        self.assertEqual(ret, True)
        self.assertEqual(info['stderr'], '')
        self.assertEqual(info['exitcode'], 0)

        for f in ('prologin.c', '_lang', 'champion.so'):
            self.assertIn(f, log)

        tgz = b64decode(compiled)
        with tempfile.TemporaryDirectory() as tmpdir:
            operations.untar(tgz, tmpdir)
            cpath = os.path.join(tmpdir, 'champion.so')
            self.assertTrue(os.access(cpath, mode=os.R_OK))
            lib = ctypes.cdll.LoadLibrary(cpath)
            self.assertEqual(lib.hello(), 42)
