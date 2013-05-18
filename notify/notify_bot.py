#!/usr/bin/env python3
#-*- encoding: utf-8 -*-

from pypeul import IRC, logger
import time
import getpass
import string
import random
import subprocess
import logging
import textwrap


logging.basicConfig(level=logging.DEBUG)

host = 'irc'
port = 6667
chan, key = '#notify', ''
login = getpass.getuser()


def gen_nick():
    return (login + '_' +
        ''.join(random.choice(string.ascii_lowercase + string.digits) for x in
        range(5)))


def notify(minutes, msg):
    msg = '<br/>'.join(textwrap.wrap(msg, 40))
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
        if 'o' in umask.user.modes_in(chan):
            if command != '!announce':
                if command == '!query' and login == l[0]:
                    l = l[1:]
                else:
                    return
            if l[0].isdigit():
                time = int(l[0])
                l = l[1:]
            else:
                time = 10
            self.notify_callback(time * 1000 * 60, ' '.join(l))

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
    run(notify)
