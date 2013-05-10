#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import subprocess
import prologin.udbsync
import sys

runner = '/var/prologin/bugs/script/rails'

env = os.environ.copy()
env['RAILSENV'] = 'production'

create_command = '''
    user = User.new({{:firstname => "{l}",:lastname=>"{l}",:mail=>"{l}@example.com"}})
    user.login = '{l}'
    user.password = '{p}'
    user.password_confirmation = '{p}'
    user.save
'''

delete_command = '''
user = User.find_by_login('{l}')
u.destroy
'''

update_command = '''
user = User.find_by_login('{l}')
user.password = '{p}'
user.password_confirmation = '{p}'
user.save!
'''

def callback(users, updates_metadata):
    commands = []
    for l, status in updates_metadata.items():
        if status == 'created':
            commands.append(create_command.format(l=l, p=users[l]['password']))
        elif status == 'deleted':
            commands.append(delete_command.format(l=l, p=users[l]['password']))
        elif status == 'updated':
            commands.append(update_command.format(l=l, p=users[l]['password']))

    with open('synctmp.rb', 'w', encoding='utf8') as f:
        f.write('\n'.join(commands))

    print('Calling rails runner...')
    subprocess.call([runner, 'runner', '-e', 'production', 'synctmp.rb'
    ], env=env, stdout=sys.stdout, stderr=sys.stderr)


c = prologin.udbsync.connect()
c.poll_updates(callback, watch={'password'})
