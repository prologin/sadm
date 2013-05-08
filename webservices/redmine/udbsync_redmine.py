#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import subprocess
import prologin.udbsync

runner = '/var/prologin/bugs/scripts/runner'

env = os.environ.copy()
env['RAILSENV'] = 'production'

create_command = '''
user = User.new({{:firstname => "{n}",:lastname=>"",:mail=>"{l}@example.com"}})
user.login = '{l}'
user.password = '{p}'
user.password_confirmation = '{p}'
user.save
'''

delete_command = '''
user = User.find('{l}')
u.destroy
'''

update_command = '''
user = User.find('{l}')
user.password = '{p}'
user.password_confirmation = '{p}'
user.save!
'''

def callback(users, updates_metadata):
    for l, status in updates_metadata.items():
        if status == 'created':
            subprocess.call([runner,
                create_command.format(
                    l=l, n=users[l]['realname'], p=users[l]['password'])
            ], env=env)
        elif status == 'deleted':
            subprocess.call([runner,
                delete_command.format(
                    l=l, p=users[l]['password'])
            ], env=env)
        elif status == 'updated':
            subprocess.call([runner,
                update_command.format(
                    l=l, p=users[l]['password'])
            ], env=env)
    
        
c = prologin.udbsync.connect()
c.poll_updates(callback, watch={'password'})
