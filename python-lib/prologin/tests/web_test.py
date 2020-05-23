import sys
import threading

import pytest
import aiohttp.web

import prologin.web


async def index_handler(request):
    return aiohttp.web.Response(text="hello world")


async def post_handler(request):
    return aiohttp.web.Response(text="this is post")


@pytest.fixture
def minimal_app(aiohttp_client):
    return prologin.web.AiohttpApp(
        [('get', '/', index_handler), ('post', '/post', post_handler)]
    ).app


@pytest.fixture
async def client(aiohttp_client, minimal_app):
    return await aiohttp_client(minimal_app)


async def test_404(client):
    assert (await client.get("/nope")).status == 404


async def test_index(client):
    assert await (await client.get("/")).text() == "hello world"


async def test_post(client):
    page = await client.get("/post")
    assert page.status == 405
    assert page.headers['Allow'] == 'POST'

    assert await (await client.post("/post")).text() == "this is post"


async def test_debug_handler_info(client):
    page = await (await client.get("/__info")).text()
    assert f"Python {sys.version}" in page
    assert "bin/python" in page
    assert "AiohttpApp in module prologin.web" in page
    assert "1 active threads" in page

    thread_id = threading.current_thread().ident
    assert f"0x{thread_id:x}" in page


async def test_debug_handler_state_empty(client):
    page = await (await client.get("/__state")).text()
    assert "{}" in page


async def test_debug_handler_state(aiohttp_client):
    app = prologin.web.AiohttpApp([])
    app.foo = {"hello": "world"}
    app.exposed_attributes = {"foo", "app"}

    client = await aiohttp_client(app.app)

    page = await (await client.get("/__state")).text()
    assert "foo" in page and "hello" in page and "world" in page
    assert "app" in page and f"0x{id(app.app):x}" in page
