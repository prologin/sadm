#!/usr/bin/env python3

import json
import logging
import os
import prologin.log
import prologin.udbsync.client
import subprocess
import sys

REDMINE_ROOT = '/var/prologin/redmine/script'
SCRIPT_PATH = os.path.join(REDMINE_ROOT, 'user_update.rb')
RUNNER = os.path.join(REDMINE_ROOT, 'rails')


def callback(users, updates_metadata):
    logging.info('Got events: %r' % updates_metadata)

    commands = []
    give_users = {}
    for login, status in updates_metadata.items():
        give_users[login] = users[login]
        commands.append((login, status))

    logging.info('Calling redmine runner user_update.rb...')

    proc = subprocess.Popen([
        RUNNER, 'runner', '-e', 'production', SCRIPT_PATH,
    ], env=ENV, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = proc.communicate(
        json.dumps({'users': give_users, 'commands': commands}).encode('utf-8')
    )

    if stderr:
        logging.error('redmine runner user_update.rb returned an error:\n%s', stderr)


if __name__ == '__main__':
    prologin.log.setup_logging('udbsync_redmine')
    ENV = os.environ.copy()
    ENV['RAILSENV'] = 'production'
    prologin.udbsync.client.connect().poll_updates(callback, watch={'password'})
