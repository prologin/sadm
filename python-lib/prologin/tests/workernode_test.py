import asyncio
import collections
import os
import prologin.rpc.server
import tempfile
import threading
import time
import tornado
import unittest
import yaml

from prologin.workernode.operations import communicate as coro_comm
from prologin.workernode.worker import WorkerNode


#################
# communicate() #
#################


def communicate(*args, **kwargs):
    return asyncio.get_event_loop().run_until_complete(coro_comm(*args, **kwargs))


class WorkerNodeCommunicate(unittest.TestCase):
    def test_simple_echo(self):
        arg = 'Votai Test.'
        code, out = communicate(['/bin/echo', '-n', arg])
        self.assertEqual(out, arg)
        self.assertEqual(code, 0)

    def test_stdin_cat(self):
        data = 'Test. La seule liste BDE doublement chaînée.'
        code, out = communicate(['/bin/cat'], data=data)
        self.assertEqual(out, data)
        self.assertEqual(code, 0)

    def test_errcode(self):
        self.assertEqual(communicate(['/bin/true'])[0], 0)
        self.assertEqual(communicate(['/bin/false'])[0], 1)

    def test_truncate_output(self):
        out = communicate(['echo', 'Test.' * 99], max_len=21)[1]
        self.assertTrue(len(out) == 21)

        out = communicate(['echo', 'Test.' * 99], max_len=0)[1]
        self.assertTrue(len(out) == 0)

        out = communicate(['echo', 'Test.' * 99], max_len=10,
                truncate_message='log truncated')[1]
        self.assertTrue(len(out) == 10 + len('log truncated'))

    def test_timeout(self):
        with self.assertRaises(asyncio.TimeoutError):
            out = communicate(['/bin/sleep', '10'], timeout=1)



#########################
# Test the method calls #
#########################

def get_worker_config(**kwargs):
    d = collections.defaultdict(str)
    d.update(kwargs)
    worker_config = '''
    master:
        host: localhost
        port: 42547
        heartbeat_secs: 5
        shared_secret: test42
        max_retries: 15
        retry_delay: 10
    worker:
        port: 42546
        available_slots: 20
        port_range_start: 40000
        port_range_end: 41000
    path:
        compile_script: {compile_script}
        stechec_server: {stechec_server}
        stechec_client: {stechec_client}
        dumper: {dumper}
        rules: /rules
        makefiles: /makefiles
    '''
    return yaml.load(worker_config.format(**d))

class DummyMaster(prologin.rpc.server.BaseRPCApp):
    def __init__(self, *args, **kwargs):
        self.calls = {}
        super().__init__(*args, **kwargs)

    @prologin.rpc.remote_method
    def update_worker(self, *args, **kwargs):
        pass

    @prologin.rpc.remote_method
    def heartbeat(self, *args, **kwargs):
        pass

    @prologin.rpc.remote_method
    def compilation_result(self, *args, **kwargs):
        self.calls['compilation_result'] = (args, kwargs)

    @prologin.rpc.remote_method
    def client_done(self, *args, **kwargs):
        self.calls['client_done'] = (args, kwargs)

    @prologin.rpc.remote_method
    def match_done(self, *args, **kwargs):
        self.calls['match_done'] = (args, kwargs)


class DummyMasterInstance(threading.Thread):
    def __init__(self, port):
        super().__init__()
        self.port = port
        self.ioloop = None

    def run(self):
        self.app = DummyMaster('testmaster')
        self.app.listen(self.port)
        self.ioloop = tornado.ioloop.IOLoop.instance()
        self.ioloop.start()

    def stop(self):
        if self.ioloop:
            self.ioloop.stop()


class WorkerInstance(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.worker = None

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.worker = WorkerNode(app_name='testworker', config=self.config,
                secret=b'test42')
        self.worker.run()

    def stop(self):
        if self.worker:
            self.worker.stop()


class WorkerNodeTest(unittest.TestCase):
    def setUp(self):
        self.scripts = {}
        for f in ['compile_script', 'stechec_server', 'stechec_client', 'dumper']:
            fd = tempfile.NamedTemporaryFile('w+', delete=False)
            os.chmod(fd.name, 0o700)
            fd.write('''#!/usr/bin/env python3
                     import sys
                     print('{}')
                     print('\n'.join(sys.argv))'''.format(f))
            self.scripts[f] = fd.name
            fd.close()
        config = get_worker_config(**self.scripts)
        self.wi = WorkerInstance(config)
        self.mi = DummyMasterInstance(42547)
        self.mi.start()
        self.wi.start()
        self.wc = prologin.rpc.client.Client('http://127.0.0.1:42546',
                secret=b'test42')
        time.sleep(0.3)

    def tearDown(self):
        self.mi.stop()
        self.wi.stop()
        for f in self.scripts.values():
            os.remove(f)

    def test_compile(self):
        self.wc.compile_champion('user1', 1001, '')
        time.sleep(2)
        self.assertIn('compilation_result', self.mi.app.calls)
