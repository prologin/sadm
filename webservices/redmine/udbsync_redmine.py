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
begin
    user = User.find_by_login('{l}')
rescue
    user = User.new({{:firstname => "{n}",:lastname=>"",:mail=>"{l}@example.com"}})
    user.login = '{l}'
    user.password = '{p}'
    user.password_confirmation = '{p}'
    user.save
end
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
            commands.append(create_command.format(
                l=l, n=users[l]['realname'], p=users[l]['password']))
        elif status == 'deleted':
            commands.append(delete_command.format(l=l, p=users[l]['password']))
        elif status == 'updated':
            commands.append(update_command.format(l=l, p=users[l]['password']))

    print(commands)

    subprocess.call([runner, 'runner', '-e', 'production'
        '\n'.join(commands)
    ], env=env, stdout=sys.stdout, stderr=sys.stderr)


c = prologin.udbsync.connect()
c.poll_updates(callback, watch={'password'})
