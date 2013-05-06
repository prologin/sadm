#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import subprocess
import prologin.udbsync

env = os.environ.copy()
env['PYTHONPATH'] = ('/var/prologin/wiki:' +
                    (env['PYTHONPATH'] if 'PYTHONPATH' in env else ''))

def callback(users, updates_metadata):
    for u in users:
        if updates_metadata[u.login] == 'created':
            subprocess.call([
                'moin', 'account', 'create',
                '--name', u.login,
                '--alias', u.login,
                '--email', u.login + '@example.com',
                '--password', u.password,
                u.password,
            ], env=env)
        elif updates_metadata[u.login] == 'updated':
            subprocess.call([
                'moin', 'account', 'resetpw',
                '--name', u.login,
                u.password,
            ], env=env)
    for login, status in updates_metadata.items():
        if status == 'deleted':
            subprocess.call([
                'moin', 'account', 'disable',
                '--name', login,
            ], env=env)
    
        
c = prologin.udbsync.connect()
c.poll_updates(callback, watch={'password'} or None)
