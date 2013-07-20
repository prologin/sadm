#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import prologin.rpc.client
import prologin.rpc.server
import unittest
import threading
import time
import tornado

class RpcServer(prologin.rpc.server.BaseRPCApp):

    @prologin.rpc.server.remote_method
    def return_number(self):
        return 42

    @prologin.rpc.server.remote_method
    def return_string(self):
        return 'prologin'

    @prologin.rpc.server.remote_method
    def return_list(self):
        return list(range(10)) 

    @prologin.rpc.server.remote_method
    def generate_numbers(self):
        for i in range(10):
            time.sleep(1)
            yield i

    @prologin.rpc.server.remote_method
    def long_polling(self):
        time.sleep(15)
        return 42

class RpcServerInstance(threading.Thread):
    def run(self):
        self.app = RpcServer('test-rpc')
        self.app.listen(42545)
        self.ioloop = tornado.ioloop.IOLoop.instance()
        self.ioloop.start()
    
    def stop(self):
        self.ioloop.stop()

class RpcTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.s = RpcServerInstance()
        cls.s.start()
        cls.c = prologin.rpc.client.Client('http://127.0.0.1:42545')

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_number(self):
        self.assertEqual(self.c.return_number(), 42)

    def test_string(self):
        self.assertEqual(self.c.return_string(), 'prologin')

    def test_list(self):
        self.assertEqual(self.c.return_list(), list(range(10)))

    def test_generator(self):
        self.assertEqual(list(self.c.generate_numbers()), list(range(10)))

    def test_long_polling(self):
        self.assertEqual(self.c.long_polling(), 42)
