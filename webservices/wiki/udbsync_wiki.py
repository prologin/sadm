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
        if updates_metadata[u] == 'created':
            subprocess.call([
                'moin', 'account', 'create',
                '--name', u.login,
                '--alias', u.login,
                '--email', u.login + '@example.com',
                '--password', u.password,
                u.password,
            ], env=env)
        elif updates_metadata[u] == 'deleted':
            subprocess.call([
                'moin', 'account', 'disable',
                '--name', u.login,
            ], env=env)
        elif updates_metadata[u] == 'updated':
            subprocess.call([
                'moin', 'account', 'resetpw',
                '--name', u.login,
                u.password,
            ], env=env)
        
        
c = prologin.udbsync.connect()
c.poll_updates(callback, watch={'password'} or None)
