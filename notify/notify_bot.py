#!/usr/bin/env python3
#-*- encoding: utf-8 -*-

from pypeul import IRC, logger
import time
import getpass
import string
import random
import subprocess
import logging


logging.basicConfig(level=logging.INFO)

host = 'irc.freenode.net'
port = 6667
chan, key = '#prologin-test', ''


def gen_nick():
    return (getpass.getuser() + '_' +
        ''.join(random.choice(string.ascii_lowercase + string.digits) for x in
        range(5)))

def notify(minutes, msg):
    subprocess.call(
        ['notify-send',
         '--urgency', 'normal',
         '--expire-time', str(minutes),
         msg])

class NotifierBot(IRC):
    def on_ready(self):
        self.join(chan, key)

    def on_channel_message(self, umask, target, msg):
        command, *l = msg.split()
        if command == '!announce' and 'o' in umask.user.modes_in(chan):
            if l[0].isdigit():
                time = int(l[0])
                l = l[1:]
            else:
                time = 2
            self.notify_callback(time * 1000 * 60, ' '.join(msg.split()[2:]))

    def on_disconnected(self):
        logger.info('Disconnected. Trying to reconnect...')
        while True:
            try:
                self.connect(host, port)
                self.ident(gen_nick())
                self.run()
                break
            except:
                logger.error('Attempt failed. Retrying in 30s...')
            time.sleep(30)


def run(callback):
    bot = NotifierBot()
    bot.notify_callback = callback
    bot.connect(host, port)
    bot.ident(gen_nick())
    bot.run()

if __name__ == '__main__':
    notify_bot.run(notify)
