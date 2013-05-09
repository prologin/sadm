#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import subprocess
import prologin.udbsync
import sys

runner = '/var/prologin/bugs/scripts/rails'

env = os.environ.copy()
env['RAILSENV'] = 'production'

create_command = '''
begin
    user = User.find('{l}')
rescue
    user = User.new({{:firstname => "{n}",:lastname=>"",:mail=>"{l}@example.com"}})
    user.login = '{l}'
    user.password = '{p}'
    user.password_confirmation = '{p}'
    user.save
end
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
            subprocess.call([runner, 'runner',
                create_command.format(
                    l=l, n=users[l]['realname'], p=users[l]['password'])
            ], env=env, stdout=sys.stdout, stderr=sys.stderr)
        elif status == 'deleted':
            subprocess.call([runner, 'runner',
                delete_command.format(
                    l=l, p=users[l]['password'])
            ], env=env, stdout=sys.stdout, stderr=sys.stderr)
        elif status == 'updated':
            subprocess.call([runner, 'runner',
                update_command.format(
                    l=l, p=users[l]['password'])
            ], env=env, stdout=sys.stdout, stderr=sys.stderr)
    
        
c = prologin.udbsync.connect()
c.poll_updates(callback, watch={'password'})
