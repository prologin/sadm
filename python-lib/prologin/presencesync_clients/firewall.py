#!/usr/bin/env python

import logging
import os
import prologin.config
import prologin.log
import prologin.mdb.client
import prologin.presencesync.client
import prologin.udb.client
import subprocess

CFG = prologin.config.load('presencesync_firewall')


def callback(logins, updates_metadata):
    logging.info('Updating firewall')

    allowed_groups = CFG['allowed_groups']

    mdb_machines = prologin.mdb.client.connect().query()  # get all machines
    udb_users = prologin.udb.client.connect().query()  # get all users

    # Flush temporary set
    subprocess.call('ipset flush tmp-allowed-internet-access', shell=True)

    # Find allowed hostnames
    allowed_hostnames = set()
    for entry in logins.values():
        for user in udb_users:
            if entry['login'] == user['login']:
                if user['group'] in allowed_groups:
                    # Add user to temporary set
                    allowed_hostnames.add(entry['hostname'])
                break # User found

    # Translate hostnames to ip
    allowed_ips = set()
    for hostname in allowed_hostnames:
        for machine in mdb_machines:
            if hostname == machine['hostname']:
                allowed_ips.add(machine['ip'])
                break # IP found

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

if __name__ == '__main__':
    prologin.log.setup_logging('presencesync_firewall')
    prologin.presencesync.client.connect().poll_updates(callback)
