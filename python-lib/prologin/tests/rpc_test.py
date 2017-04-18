#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import asyncio
import prologin.rpc.client
import prologin.rpc.server
import unittest
import threading
import time


class RpcServer(prologin.rpc.server.BaseRPCApp):
    @prologin.rpc.remote_method
    async def return_number(self):
        return 42

    @prologin.rpc.remote_method
    async def return_string(self):
        return 'prologin'

    @prologin.rpc.remote_method
    async def return_list(self):
        return list(range(10))

    @prologin.rpc.remote_method
    async def return_input(self, inp):
        return inp

    @prologin.rpc.remote_method
    async def return_args_kwargs(self, arg1, arg2, *, kw1=None, kw2=None):
        return [[arg1, arg2], {'kw1': kw1, 'kw2': kw2}]

class RpcServerInstance(threading.Thread):
    def __init__(self, port, secret=None):
        super().__init__()
        self.port = port
        self.secret = secret

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.app = RpcServer('test-rpc', secret=self.secret, loop=self.loop)
        self.app.run(port=42545, print=lambda *_:None)

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)

class RpcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = prologin.rpc.client.SyncClient('http://127.0.0.1:42545')
        cls.s = RpcServerInstance(42545)
        cls.s.start()
        time.sleep(0.5) # Let it start

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_number(self):
        self.assertEqual(self.c.return_number(), 42)

    def test_string(self):
        self.assertEqual(self.c.return_string(), 'prologin')

    def test_list(self):
        self.assertEqual(self.c.return_list(), list(range(10)))

    def test_nested(self):
        obj = {'test': 72, 'list': [1, 42, 33, {'object': '3'}]}
        self.assertEqual(self.c.return_input(obj), obj)

    def test_args_kwargs(self):
        res = self.c.return_args_kwargs(1, 'c', kw1='a', kw2=None)
        self.assertEqual(res, [[1, 'c'], {'kw1': 'a', 'kw2': None}])


class RpcAsyncTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = prologin.rpc.client.Client('http://127.0.0.1:42545')
        cls.s = RpcServerInstance(42545)
        cls.s.start()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_async_number(self):
        loop = asyncio.get_event_loop()
        self.assertEqual(loop.run_until_complete(self.c.return_number()), 42)


class RpcSecretTest(unittest.TestCase):
    GOOD_SECRET = b'secret42'
    BAD_SECRET = b'secret51'

    @classmethod
    def setUpClass(cls):
        cls.s = RpcServerInstance(42545, secret=cls.GOOD_SECRET)
        cls.s.start()
        time.sleep(0.5) # Let it start

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_good_secret(self):
        c = prologin.rpc.client.SyncClient('http://127.0.0.1:42545',
                                           secret=self.GOOD_SECRET)
        self.assertEqual(c.return_number(), 42)

    def test_bad_secret(self):
        c = prologin.rpc.client.SyncClient('http://127.0.0.1:42545',
                                           secret=self.BAD_SECRET)
        with self.assertRaises(prologin.rpc.client.RemoteError) as e:
            c.return_number()
        self.assertEqual(e.exception.type, 'BadToken')

    def test_missing_secret(self):
        c = prologin.rpc.client.SyncClient('http://127.0.0.1:42545')
        with self.assertRaises(prologin.rpc.client.RemoteError) as e:
            c.return_number()
        self.assertEqual(e.exception.type, 'MissingToken')
