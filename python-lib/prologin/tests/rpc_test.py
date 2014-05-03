#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import asyncio
import prologin.rpc.client
import prologin.rpc.server
import unittest
import threading
import time
import tornado


class RpcServer(prologin.rpc.server.BaseRPCApp):

    @prologin.rpc.remote_method
    def return_number(self):
        return 42

    @prologin.rpc.remote_method
    def return_string(self):
        return 'prologin'

    @prologin.rpc.remote_method
    def return_list(self):
        return list(range(10))

    @prologin.rpc.remote_method
    def generate_numbers(self):
        for i in range(10):
            time.sleep(0.1)
            yield i

    @prologin.rpc.remote_method
    def long_generator(self):
        yield True
        time.sleep(15)
        yield True

    @prologin.rpc.remote_method
    def instant_generator(self):
        yield True
        yield True

    @prologin.rpc.remote_method
    def long_polling(self):
        time.sleep(5)
        return 42

class RpcServerInstance(threading.Thread):
    def __init__(self, port):
        super().__init__()
        self.port = port

    def run(self):
        self.app = RpcServer('test-rpc')
        self.app.listen(self.port)
        self.ioloop = tornado.ioloop.IOLoop.instance()
        self.ioloop.start()

    def stop(self):
        self.ioloop.stop()

class RpcTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = prologin.rpc.client.Client('http://127.0.0.1:42545')
        cls.s = RpcServerInstance(42545)
        cls.s.start()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_number(self):
        self.assertEqual(self.c.return_number(), 42)

    def test_string(self):
        self.assertEqual(self.c.return_string(), 'prologin')

    def test_list(self):
        self.assertEqual(self.c.return_list(), list(range(10)))

    @unittest.skip("readline() returns nothing, to investigate")
    def test_generator(self):
        self.assertEqual(list(self.c.generate_numbers()), list(range(10)))

    @unittest.skip("we need a thread pool for these")
    def test_parallel_generators(self):
        before = time.time()
        g1 = self.c.long_generator()
        g2 = self.c.instant_generator()
        next(g1)
        next(g2)
        self.assertTrue(time.time() - before < 10)

    def test_long_polling(self):
        self.assertEqual(self.c.long_polling(), 42)


class RpcAsyncTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = prologin.rpc.client.Client('http://127.0.0.1:42546',
                async=True)
        cls.s = RpcServerInstance(42546)
        cls.s.start()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_async_number(self):
        loop = asyncio.get_event_loop()
        self.assertEqual(loop.run_until_complete(self.c.return_number()), 42)
