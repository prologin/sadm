#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import subprocess
import prologin.udbsync

env = os.environ.copy()
env['PYTHONPATH'] = ('/var/prologin/wiki:' +
                    (env['PYTHONPATH'] if 'PYTHONPATH' in env else ''))

def callback(users, updates_metadata):
    for login, status in updates_metadata.items():
        if status == 'deleted':
            subprocess.call([
                'moin', 'account', 'disable',
                '--name', login,
                '--config-dir', '/var/prologin/wiki'
            ], env=env)
        elif status == 'created':
            subprocess.call([
                'moin', 'account', 'create',
                '--name', login,
                '--alias', login,
                '--email', login + '@example.com',
                '--password', users[login].password,
                '--config-dir', '/var/prologin/wiki'
            ], env=env)
        elif status == 'updated':
            subprocess.call([
                'moin', 'account', 'resetpw',
                '--name', login,
                users[login].password,
                '--config-dir', '/var/prologin/wiki'
            ], env=env)
    
        
c = prologin.udbsync.connect()
c.poll_updates(callback, watch={'password'})
