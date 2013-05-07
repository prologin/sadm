#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import prologin.udbsync


def callback(users, updates_metadata):
    os.makedirs('/root/.ssh/', mode=0o700, exist_ok=True)
    with open('/root/.ssh/authorized_keys', 'w+') as f:
        f.write('\n'.join(map(lambda x: x.ssh_key, users.values())))

        
c = prologin.udbsync.connect()
c.poll_updates(callback, watch={'ssh_key'})
