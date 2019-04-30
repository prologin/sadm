#!/usr/bin/env python3

import asyncio
import contextlib
import logging
import socket
import threading
import time
import unittest

import prologin.rpc.client
import prologin.rpc.server


@contextlib.contextmanager
def disable_logging():
    logger = logging.getLogger()
    logger.disabled = True
    yield
    logger.disabled = False


class RPCServer(prologin.rpc.server.BaseRPCApp):
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

    @prologin.rpc.remote_method
    async def raises_valueerror(self):
        # we disable exception logging to avoid seeing the intentional raise
        with disable_logging():
            raise ValueError("Monde de merde.")

    @prologin.rpc.remote_method(auth_required=False)
    async def public_hello(self):
        return 'hello'


URL = 'http://127.0.0.1:42545'


class RPCServerInstance(threading.Thread):
    def __init__(self, port=42545, secret=None, delay=0):
        super().__init__()
        self.port = port
        self.secret = secret
        self.delay = delay

    def run(self):
        time.sleep(self.delay)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.app = RPCServer('test-rpc', secret=self.secret, loop=self.loop)
        self.app.run(port=self.port)

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)


class RPCTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = prologin.rpc.client.SyncClient(URL)
        cls.s = RPCServerInstance()
        cls.s.start()
        time.sleep(0.5)  # Let it start

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()
        time.sleep(0.5)

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

    def test_missing_method(self):
        with self.assertRaises(prologin.rpc.client.RemoteError) as e:
            self.c.missing_method()
        self.assertEqual(e.exception.type, 'MethodError')

    def test_raises_valueerror(self):
        with self.assertRaises(prologin.rpc.client.RemoteError) as e:
            self.c.raises_valueerror()
        self.assertEqual(e.exception.type, 'ValueError')
        self.assertEqual(e.exception.message, 'Monde de merde.')


class RPCAsyncTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = prologin.rpc.client.Client(URL)
        cls.s = RPCServerInstance()
        cls.s.start()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()
        time.sleep(0.5)

    def test_async_number(self):
        loop = asyncio.get_event_loop()
        self.assertEqual(loop.run_until_complete(self.c.return_number()), 42)


class RPCSecretTest(unittest.TestCase):
    GOOD_SECRET = b'secret42'
    BAD_SECRET = b'secret51'

    @classmethod
    def setUpClass(cls):
        cls.s = RPCServerInstance(secret=cls.GOOD_SECRET)
        cls.s.start()
        time.sleep(0.5)  # Let it start

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_good_secret(self):
        c = prologin.rpc.client.SyncClient(URL, secret=self.GOOD_SECRET)
        self.assertEqual(c.return_number(), 42)

    def test_bad_secret(self):
        c = prologin.rpc.client.SyncClient(URL, secret=self.BAD_SECRET)
        with self.assertRaises(prologin.rpc.client.RemoteError) as e:
            c.return_number()
        self.assertEqual(e.exception.type, 'BadToken')

    def test_missing_secret(self):
        c = prologin.rpc.client.SyncClient(URL)
        with self.assertRaises(prologin.rpc.client.RemoteError) as e:
            c.return_number()
        self.assertEqual(e.exception.type, 'MissingToken')

    def test_public_good_secret(self):
        c = prologin.rpc.client.SyncClient(URL, secret=self.GOOD_SECRET)
        self.assertEqual(c.public_hello(), 'hello')

    def test_public_bad_secret(self):
        c = prologin.rpc.client.SyncClient(URL, secret=self.BAD_SECRET)
        self.assertEqual(c.public_hello(), 'hello')

    def test_public_missing_secret(self):
        c = prologin.rpc.client.SyncClient(URL)
        self.assertEqual(c.public_hello(), 'hello')


@unittest.skip("FIXME: Race conditions, address already in use")
class RPCRetryTest(unittest.TestCase):
    def test_retry_enough(self):
        s = RPCServerInstance(delay=1)  # 1 second to start
        s.start()
        c = prologin.rpc.client.SyncClient(URL)
        with disable_logging():
            self.assertEqual(c.return_number(max_retries=1, retry_delay=2), 42)
        s.stop()

    def test_retry_notenough(self):
        s = RPCServerInstance(delay=1)
        s.start()
        c = prologin.rpc.client.SyncClient(URL)
        with self.assertRaises(socket.error):
            with disable_logging():
                c.return_number(max_retries=0)
        s.stop()

    def test_retry_tooslow(self):
        s = RPCServerInstance(delay=1)
        s.start()
        c = prologin.rpc.client.SyncClient(URL)
        with self.assertRaises(socket.error):
            with disable_logging():
                c.return_number(max_retries=1, retry_delay=0.2)
        s.stop()
