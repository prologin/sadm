# Copyright (c) 2013 Association Prologin <info@prologin.org>
#
# Prologin-SADM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prologin-SADM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prologin-SADM.  If not, see <http://www.gnu.org/licenses/>.

"""Provides utilities for Prologin web applications. Everything should be
prologinized like this:

    import prologin.web
    application = prologin.web.AiohttpApp(routes)

This initializes logging using prologin.log, and maps some special URLs to
debug pages (WARNING: no authentication is done, this could leak secrets):
  * /__info
    Returns Python version and a bunch of system info.
  * /__threads
    Shows the stack of all threads & asyncio tasks in the process.
  * /__state
    Shows a state dump. Applications choose what to expose here.
"""

import asyncio
import html
import io
import os
import pprint
import sys
import threading
import traceback
from typing import Mapping, Any, Set

import aiohttp.web
import aiohttp_wsgi


def html_response(text):
    return aiohttp.web.Response(
        text=text, content_type="text/html", charset="utf-8"
    )


def debug_header():
    return (
        "<style>body { font-family:monospace; white-space:pre-wrap; }</style>"
        + " ⋅ ".join(
            f"<a href='{url}'>{html.escape(text)}</a>"
            for url, text in (
                ("/__info", "Summary"),
                ("/__threads", "Threads & coroutines"),
                ("/__state", "State dump"),
            )
        )
        + "\n\n"
    )


class AiohttpApp:
    exposed_attributes: Set[str] = set()
    """Instance attributes to expose on the /__state page. For more control,
    override exposed_state()."""

    def __init__(self, routes, **kwargs):
        self.app = aiohttp.web.Application(**kwargs)
        for route in routes:
            self.app.router.add_route(*route)
        self.app.add_routes(
            [
                aiohttp.web.get("/__info", self.info_handler),
                aiohttp.web.get("/__threads", self.threads_handler),
                aiohttp.web.get("/__state", self.state_handler),
            ]
        )

    async def info_handler(self, request):
        return html_response(
            debug_header()
            + html.escape(
                f"Python {sys.version}\n\n"
                f"Running {sys.executable} as {os.getuid()}:{os.getgid()}\n\n"
                f"{self.__class__.__name__} in module "
                f"{self.__class__.__module__}\n\n"
                f"{threading.active_count()} active threads ⋅ "
                f"current: 0x{threading.current_thread().ident:x}\n"
                f"{len(asyncio.all_tasks())} asyncio tasks"
            )
        )

    async def threads_handler(self, request):
        e = html.escape
        frames = sys._current_frames()
        response = [
            debug_header(),
            "<h3 id='threads'>",
            e(f"{len(frames)} active threads"),
            " <small><a href='#tasks'>Go to tasks</a></small></h3>",
        ]

        current_thread = threading.current_thread()
        for id, frame in frames.items():
            tb = "".join(traceback.format_stack(frame))
            text = e(f"Thread 0x{id:x}:")
            if id == current_thread.ident:
                text = f"<b title='Current thread'>{text}</b>"
            response.append(text)
            response.append(f"\n{tb}\n")

        tasks = asyncio.all_tasks()
        response.extend(
            [
                "<h3 id='tasks'>",
                e(f"{len(tasks)} asyncio tasks"),
                " <small><a href='#threads'>Go to threads</a></small></h3>",
            ]
        )
        current_task = asyncio.current_task()
        for task in tasks:
            # So yeah, traceback.format_stack cannot be used on task stacks,
            # because something something Python and consistent APIs. Also it's
            # easy to make task.print_stack() error out. asyncio is basically
            # still in beta in 2020Q2.
            sio = io.StringIO()
            try:
                task.print_stack(file=sio)
            except:
                sio.write("Python is broken.")
            text = f"Task {task.get_name()}:"
            if task == current_task:
                text = f"<b>{text}</b>"
            response.append(text)
            response.append(e(f"\n{sio.getvalue()}\n"))

        return html_response("".join(response))

    async def state_handler(self, request):
        state = html.escape(pprint.pformat(await self.exposed_state()))
        return html_response(debug_header() + state)

    async def exposed_state(self) -> Mapping[str, Any]:
        """Returns dict of str -> object to expose on the /__state page.

        By default, this exposes attributes from :attr:`exposed_attributes`.
        """
        return {
            attr: getattr(self, attr)
            for attr in self.exposed_attributes
            if hasattr(self, attr)
        }

    def add_wsgi_app(self, wsgi_app):
        wsgi_handler = aiohttp_wsgi.WSGIHandler(wsgi_app)
        self.app.router.add_route('*', '/{path_info:.*}', wsgi_handler)

    def run(self, **kwargs):
        aiohttp.web.run_app(self.app, print=lambda *_: None, **kwargs)


if __name__ == '__main__':
    # Demo app. Open http://localhost:8000/__info to explore debug endpoints.
    app = AiohttpApp([])
    app.exposed_attributes = {'app'}
    app.run(port=8000)
