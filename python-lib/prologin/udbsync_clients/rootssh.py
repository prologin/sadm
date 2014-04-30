#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import prologin.udbsync.client


def callback(users, updates_metadata):
    os.makedirs('/root/.ssh/', mode=0o700, exist_ok=True)
    with open('/root/.ssh/authorized_keys', 'w') as f:
        l = [u['ssh_key'] for u in users.values() if u['group'] == 'root']
        l = [k for k in l if k] + ['']
        f.write('\n'.join(l))

if __name__ == '__main__':
    c = prologin.udbsync.client.connect()
    c.poll_updates(callback, watch={'ssh_key'})
