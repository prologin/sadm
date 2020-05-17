import asyncio
import contextlib
import logging

import pytest

import prologin.rpc.client
import prologin.rpc.server


@pytest.fixture(autouse=True)
def module_config(proloconf):
    proloconf("timeauth", enabled=True)


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
    async def count(self, n):
        if n == float('inf'):
            while True:
                yield 42
                await asyncio.sleep(0.01)
        else:
            for i in range(n):
                yield i

    @prologin.rpc.remote_method
    async def return_args_kwargs(self, arg1, arg2, *, kw1=None, kw2=None):
        return [[arg1, arg2], {'kw1': kw1, 'kw2': kw2}]

    @prologin.rpc.remote_method
    async def raises_valueerror(self):
        # Disable exception logging to avoid seeing the intentional raise.
        with disable_logging():
            raise ValueError("Monde de merde.")

    @prologin.rpc.remote_method(auth_required=False)
    async def public_hello(self):
        return 'hello'


def with_secret(secret):
    def wrapper(f):
        f.secret = secret
        return f

    return wrapper


@pytest.fixture
def rpc_server(request):
    secret = (
        request.function.secret
        if hasattr(request.function, 'secret')
        else None
    )
    return RPCServer(secret=secret)


@pytest.fixture
async def http_client(aiohttp_client, aiohttp_trace_ended, rpc_server):
    trace, _ = aiohttp_trace_ended
    return await aiohttp_client(rpc_server.app, trace_configs=[trace])


@pytest.fixture
async def rpc_client(http_client, rpc_server):
    return prologin.rpc.client.Client("/", http_client=http_client)


async def test_number(rpc_client):
    assert (await rpc_client.return_number()) == 42


async def test_string(rpc_client):
    assert (await rpc_client.return_string()) == 'prologin'


async def test_list(rpc_client):
    assert (await rpc_client.return_list()) == list(range(10))


async def test_nested(rpc_client):
    obj = {'test': 72, 'list': [1, 42, 33, {'object': '3'}]}
    assert (await rpc_client.return_input(obj)) == obj


async def test_args_kwargs(rpc_client):
    res = rpc_client.return_args_kwargs(1, 'c', kw1='a', kw2=None)
    assert (await res) == [[1, 'c'], {'kw1': 'a', 'kw2': None}]


async def test_missing_method(rpc_client):
    with pytest.raises(prologin.rpc.client.RemoteError) as e:
        await rpc_client.missing_method()
    assert e.value.type == 'MethodError'


async def test_raises_valueerror(rpc_client):
    with pytest.raises(prologin.rpc.client.RemoteError) as e:
        await rpc_client.raises_valueerror()
    assert e.value.type == 'ValueError'
    assert e.value.message == 'Monde de merde.'


async def test_call_normal_method_as_generate(rpc_client):
    with pytest.raises(AttributeError, match="__aexit__"):
        async with await rpc_client.return_string() as gen:
            async for x in gen:
                pass


async def test_generator(rpc_client):
    async with await rpc_client.count(n=4) as gen:
        msgs = [msg async for msg in gen]
    assert msgs == [0, 1, 2, 3]


async def test_infinite_generator(rpc_client, aiohttp_trace_ended):
    async def read_n(n):
        msgs = []
        async with await rpc_client.count(float('inf')) as gen:
            async for msg in gen:
                msgs.append(msg)
                if len(msgs) == n:
                    return msgs

    _, ended_urls = aiohttp_trace_ended
    ended_urls.clear()

    # Stop reading early.
    assert (await read_n(2)) == [42, 42]
    # Connection was closed cleanly.
    assert sum(1 for url in ended_urls if "/count" in url) == 1
    ended_urls.clear()

    # Read without limit for a while. Cancel the reading coroutine.
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(read_n(0), timeout=0.5)
    # Connection was closed cleanly.
    assert sum(1 for url in ended_urls if "/count" in url) == 1
    ended_urls.clear()

    # We can resume reading.
    assert (await read_n(3)) == [42, 42, 42]
    # Connection was closed cleanly.
    assert sum(1 for url in ended_urls if "/count" in url) == 1


GOOD_SECRET = b'secret42'
BAD_SECRET = b'secret51'


@with_secret(GOOD_SECRET)
async def test_good_secret(rpc_client):
    rpc_client._secret = GOOD_SECRET
    assert (await rpc_client.return_number()) == 42


@with_secret(GOOD_SECRET)
async def test_bad_secret(rpc_client):
    rpc_client._secret = BAD_SECRET
    with pytest.raises(prologin.rpc.client.RemoteError) as e:
        await rpc_client.return_number()
    assert e.value.type == 'BadToken'


@with_secret(GOOD_SECRET)
async def test_missing_secret(rpc_client):
    with pytest.raises(prologin.rpc.client.RemoteError) as e:
        await rpc_client.return_number()
    assert e.value.type == 'MissingToken'


@with_secret(GOOD_SECRET)
async def test_public_good_secret(rpc_client):
    rpc_client._secret = GOOD_SECRET
    assert (await rpc_client.public_hello()) == 'hello'


@with_secret(GOOD_SECRET)
async def test_public_bad_secret(rpc_client):
    rpc_client._secret = BAD_SECRET
    assert (await rpc_client.public_hello()) == 'hello'


@with_secret(GOOD_SECRET)
async def test_public_missing_secret(rpc_client):
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
