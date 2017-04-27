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


def update_firewall(client):
    logging.info('Updating firewall')

    allowed_groups = CFG['allowed_groups']

    mdb_machines = prologin.mdb.client.connect().query()  # get all machines
    udb_users = prologin.udb.client.connect().query()  # get all users
    presence_data = client.get_list()  # get presence list

    # Flush temporary set
    subprocess.call('ipset flush tmp-allowed-internet-access', shell=True)

    # Find allowed hostnames
    allowed_hostnames = set()
    for login, hostname in presence_data.items():
        for user in udb_users:
            if login == user['login']:
                if user['group'] in allowed_groups:
                    # Add user to temporary set
                    allowed_hostnames.add(hostname)
                break  # User found

    # Translate hostnames to ip
    allowed_ips = set()
    for hostname in allowed_hostnames:
        for machine in mdb_machines:
            if hostname == machine['hostname']:
                allowed_ips.add(machine['ip'])
                break  # IP found

    # Add organizers machines
    for machine in mdb_machines:
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
    executor_lock = threading.Lock()

    def callback(values, meta):
        with executor_lock:
            update_firewall(presencesync_client)

    tasks = []
    for client in (mdbsync_client, udbsync_client, presencesync_client):
        tasks.append(loop.run_in_executor(None, client.poll_updates, callback))
    await asyncio.wait(tasks)


if __name__ == '__main__':
    prologin.log.setup_logging('presencesync_firewall')
    asyncio.get_event_loop().run_until_complete(poll_all())
