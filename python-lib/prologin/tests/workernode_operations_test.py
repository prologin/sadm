import asyncio
import ctypes
import io
import os
import pathlib
import tarfile
import tempfile
import unittest

from base64 import b64decode, b64encode

from prologin.workernode import operations


# compilation tests

def get_champion_tgz(name):
    champion_path = (pathlib.Path(__file__).parent
                     / 'workernode_champions' / name).resolve()
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        tar.add(str(champion_path), arcname='')
    return b64encode(out.getvalue())


class CompilationTest(unittest.TestCase):
    def test_compile_simple(self):
        ctgz = get_champion_tgz('helloworld')

        with tempfile.TemporaryDirectory() as makefiles:
            makefiles_p = pathlib.Path(makefiles)
            makefile = (makefiles_p / 'Makefile-cxx')
            with makefile.open('w') as mkf:
                mkf.write('''\
all: champion.so
champion.so: prologin.cc
\tgcc -shared -fPIE prologin.cc -o champion.so
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

        for f in ('prologin.hh', 'prologin.cc', '_lang', 'champion.so'):
            self.assertIn(f, log)

        tgz = b64decode(compiled)
        with tempfile.TemporaryDirectory() as tmpdir:
            operations.untar(tgz, tmpdir)
            cpath = os.path.join(tmpdir, 'champion.so')
            self.assertTrue(os.access(cpath, mode=os.R_OK))
            lib = ctypes.cdll.LoadLibrary(cpath)
            self.assertEqual(lib.hello(), 42)
