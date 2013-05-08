#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import prologin.udbsync


def callback(users, updates_metadata):
    os.makedirs('/root/.ssh/', mode=0o700, exist_ok=True)
    with open('/root/.ssh/authorized_keys', 'w') as f:
        l = [u['ssh_key'] for u in users.values() if u['utype'] == 'root']
        f.write('\n'.join(l))

c = prologin.udbsync.connect()
c.poll_updates(callback, watch={'ssh_key'})
