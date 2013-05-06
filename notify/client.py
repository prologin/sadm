#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import subprocess
import notify_bot


def callback(minutes, msg):
    subprocess.call(
        ['notify-send',
         '--urgency', 'normal',
         '--expire-time', str(minutes),
         msg])


if __name__ == '__main__':
    notify_bot.run(callback)
