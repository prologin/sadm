from unittest.mock import AsyncMock

import aiohttp
import pytest


@pytest.fixture
def proloconf(mocker):
    """Mocks :func:`prologin.config.load` for a given profile.

    Usage to override the "udbsync" profile with one "foo" config key::

        @pytest.fixture
        def myconf(proloconf):
            proloconf("udbsync", foo="bar")
            # Feel free to make other calls to proloconf() here.

        def test_something(myconf):
            ...

    If all tests in a file requires the same conf, use autoload=True::

        @pytest.fixture(autoload=True)
        def myconf_autoused(proloconf):
            proloconf("udbsync", foo="bar")

        def test_something():  # No need to pass it as an argument.
            ...
    """
    config_registry = {}

    def mocked_loader(profile):
        try:
            return config_registry[profile]
        except KeyError:
            raise KeyError(
                f"Application loads config profile '{profile}', which is not "
                f"configured in proloconf fixture."
            ) from None

    def configure_func(profile, **kwargs):
        config_registry[profile] = kwargs

    config_load = mocker.patch("prologin.config.load")
    config_load.side_effect = mocked_loader
    yield configure_func
    config_load.stop()


@pytest.fixture
def aiohttp_trace_ended():
    """Retains URLs of ended requests. Useful to check they were closed.

    Typical usage::

        # aiohttp_client fixture is provided by pytest-aiohttp.
        def test_something(aiohttp_client, aiohttp_trace_ended):
            trace, ended_urls = aiohttp_trace_ended
            app = create_aiohttp_app()
            client = await aiohttp_client(app, trace_configs=[trace])

            await client.get("/foo")
            assert "/foo" in ended_urls[0]
    """
    ended_request_urls = []

    async def on_request_end(session, trace_config_ctx, params):
        ended_request_urls.append(str(params.url))

    trace = aiohttp.TraceConfig()
    trace.on_request_end.append(on_request_end)
    return trace, ended_request_urls


@pytest.fixture
def udb(mocker):
    connect = mocker.patch("prologin.udb.client.connect")
    connect.return_value = AsyncMock()
    return connect.return_value


@pytest.fixture
def mdb(mocker):
    connect = mocker.patch("prologin.mdb.client.connect")
    connect.return_value = AsyncMock()
    return connect.return_value
