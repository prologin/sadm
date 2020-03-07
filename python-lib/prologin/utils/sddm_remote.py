#!/opt/prologin/venv/bin/python

import asyncio
import aiohttp
import json
from aiohttp import web, ClientSession

admins = set()
clients = set()


async def broadcast_to(people, msg):
    if not people:
        return
    await asyncio.wait([ws.send_str(msg) for ws in people])


async def sddm_handler(request):
    ws = web.WebSocketResponse()
    ws.request = request

    try:
        await ws.prepare(request)
        print(f"Client joined: {request.remote}")
        clients.add(ws)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await broadcast_to(admins, msg.data)

        return ws

    finally:
        print(f"Client gone: {ws}")
        clients.discard(ws)


async def admin_handler(request):
    ws = web.WebSocketResponse()
    ws.request = request

    try:
        await ws.prepare(request)
        print(f"Admin joined: {ws}")
        admins.add(ws)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                order = json.loads(msg.data)
                await broadcast_to(clients, json.dumps(order))

        return ws

    finally:
        print(f"Admin gone: {ws}")
        admins.discard(ws)


if __name__ == '__main__':
    app = web.Application()
    app.add_routes(
        [web.get('/', sddm_handler), web.get('/admin', admin_handler),]
    )
    web.run_app(app, host='0.0.0.0', port=7766)
