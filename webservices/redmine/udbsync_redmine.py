#!/usr/bin/env python3

import json
import os
import prologin.udbsync
import subprocess
import sys

SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'user_update.rb',
)

RUNNER = '/var/prologin/bugs/script/rails'


def callback(users, updates_metadata):
    commands = []
    give_users = {}
    for login, status in updates_metadata.items():
        give_users[login] = users[login]
        commands.append((login, status))

    print('Calling rails runner...')
    proc = subprocess.Popen([
        RUNNER, 'runner', '-e', 'production', SCRIPT_PATH,
    ], env=ENV, stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr)

    proc.communicate(
        json.dumps({'users': give_users, 'commands': commands}).encode('ascii')
    )


if __name__ == '__main__':
    ENV = os.environ.copy()
    ENV['RAILSENV'] = 'production'
    c = prologin.udbsync.connect()
    c.poll_updates(callback, watch={'password'})
