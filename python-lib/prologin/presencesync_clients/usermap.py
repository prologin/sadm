#! /usr/bin/env python3

import asyncio
import logging
import prologin.config
import prologin.log
import prologin.mdbsync.client
import prologin.presencesync.client
import prologin.udbsync.client
import subprocess
import xml.etree.ElementTree as ET

"""Generate a map of connected contestants

The map generation uses two inputs:

    - the PresenceSync client API, to get information about connected users and
      their location
    - an single SVG pattern map of rooms

To create such a map, just draw what you want on an SVG image and put where you
want <text> objects with *exactly* two lines: the first must be the exact
machine name (e.g. "pas-r01p02") and the second can be whatever you want (it
will be replaced by the login of the connected contestants.

Look at the provided "example.svg" SVG pattern map for a fully working
example.
"""


CFG = prologin.config.load('presencesync_usermap')


G_TAG = '{http://www.w3.org/2000/svg}g'
RECT_TAG = '{http://www.w3.org/2000/svg}rect'
TEXT_TAG = '{http://www.w3.org/2000/svg}text'
TSPAN_TAG = '{http://www.w3.org/2000/svg}tspan'

# CSS style for location labels: first line is for the machine name line,
# second one is for the login line.

STYLES = {
    'connected_user': (
        'font-weight: bold;',
        'fill: #208020; font-weight: bold;'
    ),
    'connected_orga': (
        'font-weight: bold;',
        'fill: #202080; font-weight: bold;'
    ),
    'connected_root': (
        'font-weight: bold;',
        'fill: #802020; font-weight: bold;'
    ),
    'disconnected': (
        'font-weight: bold;',
        'fill: #b0b0b0; font-style: italic;'
    ),
}


def fill_rect(rect, status=True, registered=False, faulty=False):
    """
    Fill the rectangle of the machine in the usermap.
    """

    style = rect.get('style', '')

    if not registered:
        rect.set('fill', '#a9d0f5')
        rect.set('style', '')
        rect.set('stroke', '#2e64fe')
    elif faulty:
        rect.set('fill', 'url(#faultystripe)')
        rect.set('stroke', '#a6a6a6')
        rect.set('style', '')
    elif not status:
        rect.set('style', rect.get('style', '') + ';' + 'fill: #ff0000')


def fill_machine(text, login=None, group=""):
    """
    Fill some text object according to the given `login`. If `login` is None,
    the machine is considered as not occupied.
    """

    if login is None:
        styles = STYLES['disconnected']
        login = 'libre'
    else:
        styles = STYLES['connected_' + group]

    text[1].text = login
    for tspan, style in zip(text, styles):
        tspan.set('style', style)


mdb_machines = {}
udb_users = {}
presence_data = {}
ping_status = {}


def generate(map_pattern, output):
    """Write the SVG user map into the `output` using the `map_pattern`
    readable file and the `logins` -> hostname mapping.
    """
    host_to_login = {
        entry['hostname']: entry['login']
        for entry in presence_data.values()
    }

    tree = ET.parse(map_pattern)
    for g in tree.getroot().iter(G_TAG):
        if not len(g) or g[0].tag != RECT_TAG or g[1].tag != TEXT_TAG:
            continue
        rect = g[0]
        text = g[1]
        if (
            len(text) == 2 and
            text[0].tag == TSPAN_TAG and
            text[1].tag == TSPAN_TAG
        ):
            machine_name = text[0].text
            login = host_to_login.get(machine_name, None)

            group = "user"  # default group
            # Search user group
            for udb_user in udb_users.values():
                if udb_user['login'] == login:
                    group = udb_user['group']
                    break

            status = ping_status.get(machine_name, True)

            faulty = False
            registered = False
            for machine in mdb_machines.values():
                if machine['hostname'] == machine_name:
                    faulty = machine['is_faulty']
                    registered = True
                    break

            fill_machine(text, login, group)
            fill_rect(rect, status, registered, faulty)

    tree.write(output, encoding='utf-8', xml_declaration=True)


def update_map():
    logging.info('Upgrade using updates')
    try:
        with open(CFG['map_pattern'], 'rb') as map_pattern:
            with open(CFG['output'], 'wb') as output:
                generate(map_pattern, output)
    except IOError as e:
        logging.exception('Cannot open files')
    except ET.ParseError as e:
        logging.exception('Cannot parse the map pattern')


async def ping_machine(hostname):
    proc = await asyncio.create_subprocess_exec(
            'ping', '-c', '1', '-W', '2', hostname,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    return hostname, (await proc.wait() == 0)


async def update_ping(loop):
    while True:
        await asyncio.sleep(5)

        try:
            tasks = [ping_machine(m['hostname']) for m in mdb_machines.values()]
            if not tasks:
                continue

            done, _ = await asyncio.wait(tasks)

            new_ping_status = {}
            for future in done:
                hostname, status = future.result()
                new_ping_status[hostname] = status

            if new_ping_status != ping_status:
                ping_status.clear()
                ping_status.update(new_ping_status)
                loop.call_soon_threadsafe(update_map)
        except:
            logging.exception('An error while pinging the machines')


async def poll_all():
    udbsync_client = prologin.udbsync.client.connect()
    mdbsync_client = prologin.mdbsync.client.connect()
    presencesync_client = prologin.presencesync.client.connect()

    loop = asyncio.get_event_loop()

    tasks = []

    def add_task(client, dict_to_update):
        def cb(values, meta):
            dict_to_update.clear()
            dict_to_update.update(values)
            loop.call_soon_threadsafe(update_map)
        tasks.append(loop.run_in_executor(None, client.poll_updates, cb))

    add_task(mdbsync_client, mdb_machines)
    add_task(udbsync_client, udb_users)
    add_task(presencesync_client, presence_data)
    tasks.append(update_ping(loop))

    await asyncio.wait(tasks)


if __name__ == '__main__':
    prologin.log.setup_logging('presencesync_usermap')
    asyncio.get_event_loop().run_until_complete(poll_all())
