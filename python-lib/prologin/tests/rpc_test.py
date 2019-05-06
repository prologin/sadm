#!/usr/bin/env python3

import aiohttp.test_utils
import contextlib
import logging
import pytest

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


class RPCServerInstance:
    def __init__(self, *, port, secret=None):
        self.port = port
        self.secret = secret
        self.app = RPCServer('test-rpc', secret=self.secret)
        self.runner = None

    async def start(self):
        self.runner = aiohttp.web.AppRunner(self.app.app)
        await self.runner.setup()
        site = aiohttp.web.TCPSite(self.runner, '127.0.0.1', self.port)
        await site.start()

    async def stop(self):
        await self.runner.cleanup()


@pytest.fixture
async def rpc_server(request, event_loop):
    port = aiohttp.test_utils.unused_port()
    url = 'http://127.0.0.1:{}'.format(port)
    secret = (request.function.secret if hasattr(request.function, 'secret')
              else None)
    server = RPCServerInstance(port=port, secret=secret)
    await server.start()
    yield url
    await server.stop()


def with_secret(secret):
    def wrapper(f):
        f.secret = secret
        return f
    return wrapper


@pytest.fixture
async def rpc_client(rpc_server):
    return prologin.rpc.client.Client(rpc_server)


@pytest.mark.asyncio
async def test_number(rpc_client):
    assert (await rpc_client.return_number()) == 42


@pytest.mark.asyncio
async def test_string(rpc_client):
    assert (await rpc_client.return_string()) == 'prologin'


@pytest.mark.asyncio
async def test_list(rpc_client):
    assert (await rpc_client.return_list()) == list(range(10))


@pytest.mark.asyncio
async def test_nested(rpc_client):
    obj = {'test': 72, 'list': [1, 42, 33, {'object': '3'}]}
    assert (await rpc_client.return_input(obj)) == obj


@pytest.mark.asyncio
async def test_args_kwargs(rpc_client):
    res = rpc_client.return_args_kwargs(1, 'c', kw1='a', kw2=None)
    assert (await res) == [[1, 'c'], {'kw1': 'a', 'kw2': None}]


@pytest.mark.asyncio
async def test_missing_method(rpc_client):
    with pytest.raises(prologin.rpc.client.RemoteError) as e:
        await rpc_client.missing_method()
    assert e.value.type == 'MethodError'


@pytest.mark.asyncio
async def test_raises_valueerror(rpc_client):
    with pytest.raises(prologin.rpc.client.RemoteError) as e:
        await rpc_client.raises_valueerror()
    assert e.value.type == 'ValueError'
    assert e.value.message == 'Monde de merde.'


GOOD_SECRET = b'secret42'
BAD_SECRET = b'secret51'


@pytest.mark.asyncio
@with_secret(GOOD_SECRET)
async def test_good_secret(rpc_server):
    rpc_client = prologin.rpc.client.Client(rpc_server, secret=GOOD_SECRET)
    assert (await rpc_client.return_number()) == 42


@pytest.mark.asyncio
@with_secret(GOOD_SECRET)
async def test_bad_secret(rpc_server):
    rpc_client = prologin.rpc.client.Client(rpc_server, secret=BAD_SECRET)
    with pytest.raises(prologin.rpc.client.RemoteError) as e:
        await rpc_client.return_number()
    assert e.value.type == 'BadToken'


@pytest.mark.asyncio
@with_secret(GOOD_SECRET)
async def test_missing_secret(rpc_server):
    rpc_client = prologin.rpc.client.Client(rpc_server)
    with pytest.raises(prologin.rpc.client.RemoteError) as e:
        await rpc_client.return_number()
    assert e.value.type == 'MissingToken'


@pytest.mark.asyncio
@with_secret(GOOD_SECRET)
async def test_public_good_secret(rpc_server):
    rpc_client = prologin.rpc.client.Client(rpc_server, secret=GOOD_SECRET)
    assert (await rpc_client.public_hello()) == 'hello'


@pytest.mark.asyncio
@with_secret(GOOD_SECRET)
async def test_public_bad_secret(rpc_server):
    rpc_client = prologin.rpc.client.Client(rpc_server, secret=BAD_SECRET)
    assert (await rpc_client.public_hello()) == 'hello'


@pytest.mark.asyncio
@with_secret(GOOD_SECRET)
async def test_public_missing_secret(rpc_server):
    rpc_client = prologin.rpc.client.Client(rpc_server)
    assert (await rpc_client.public_hello()) == 'hello'


# TODO: convert this to pytest
"""
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
"""
