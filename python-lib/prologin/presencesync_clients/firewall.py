#!/usr/bin/env python

import asyncio
import logging
import functools
import prologin.config
import prologin.log
import prologin.mdb.client
import prologin.mdbsync.client
import prologin.presencesync.client
import prologin.udb.client
import prologin.udbsync.client
import subprocess
import threading

CFG = prologin.config.load('presencesync_firewall')


mdb_machines = {}
udb_users = {}
presence_data = {}


def update_firewall():
    # Don't do anything if the machines and user are not initialized
    if not mdb_machines or not udb_users:
        return

    logging.info('Updating firewall')

    allowed_groups = CFG['allowed_groups']

    # Flush temporary set
    subprocess.call('ipset flush tmp-allowed-internet-access', shell=True)

    # Find allowed hostnames
    allowed_hostnames = set()
    for entity in presence_data.values():
        if udb_users[entity['login']]['group'] in allowed_groups:
            # Add user to temporary set
            allowed_hostnames.add(entity['hostname'])

    # Translate hostnames to ip
    allowed_ips = set()
    for hostname in allowed_hostnames:
        for machine in mdb_machines.values():
            if hostname == machine['hostname']:
                allowed_ips.add(machine['ip'])
                break  # IP found

    # Add organizers machines
    for machine in mdb_machines.values():
        if machine['mtype'] == 'orga':
            allowed_ips.add(machine['ip'])

    for ip in allowed_ips:
        subprocess.call('ipset add tmp-allowed-internet-access %s' % ip,
                        shell=True)

    # Swap sets, supposed atomic operation
    subprocess.call('ipset swap tmp-allowed-internet-access '
                    'allowed-internet-access', shell=True)


async def poll_all():
    mdbsync_client = prologin.mdbsync.client.connect()
    udbsync_client = prologin.udbsync.client.connect()
    presencesync_client = prologin.presencesync.client.connect()

    loop = asyncio.get_event_loop()

    tasks = []

    def add_task(client, dict_to_update):
        def cb(values, meta):
            dict_to_update.clear()
            dict_to_update.update(values)
            loop.call_soon_threadsafe(update_firewall)
        tasks.append(loop.run_in_executor(None, client.poll_updates, cb))

    add_task(mdbsync_client, mdb_machines)
    add_task(udbsync_client, udb_users)
    add_task(presencesync_client, presence_data)

    await asyncio.wait(tasks)


if __name__ == '__main__':
    prologin.log.setup_logging('presencesync_firewall')
    asyncio.get_event_loop().run_until_complete(poll_all())
