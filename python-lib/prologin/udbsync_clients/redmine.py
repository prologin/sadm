#!/usr/bin/env python3

import json
import logging
import os
import prologin.log
import prologin.udbsync.client
import subprocess

# We assume the 'redmine' RVM environment exists and has everything setup properly.
# This is true if installed with respect to the docs.

SCRIPT_PATH = '/var/prologin/redmine/script/user_update.rb'
RUNNER = ('source /usr/local/rvm/environments/redmine && '
          '/var/prologin/redmine/bin/rails runner -e production ' + SCRIPT_PATH)


def callback(users, updates_metadata):
    logging.info('Got events: %r' % updates_metadata)

    commands = []
    give_users = {}
    for login, status in updates_metadata.items():
        give_users[login] = users[login]
        commands.append((login, status))

    logging.info('Calling redmine runner user_update.rb...')

    proc = subprocess.Popen([
        'sh', '-c', RUNNER,
    ], env=ENV, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = proc.communicate(
        json.dumps({'users': give_users, 'commands': commands}).encode('utf-8')
    )

    if stderr:
        logging.error('redmine runner user_update.rb returned an error:\n%s', stderr.decode('utf-8'))


if __name__ == '__main__':
    prologin.log.setup_logging('udbsync_redmine')
    ENV = os.environ.copy()
    ENV['RAILSENV'] = 'production'
    prologin.udbsync.client.connect().poll_updates(callback, watch={'password'})
