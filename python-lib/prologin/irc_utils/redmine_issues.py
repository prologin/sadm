from irc3.plugins.command import command
from threading import Lock
import asyncio
import irc3
import json
import logging
import prologin.config
import prologin.log
import socket


@irc3.plugin
class RedmineIssuePlugin:
    requires = [
        'irc3.plugins.core',
        'irc3.plugins.userlist',
        'irc3.plugins.command',
        'irc3.plugins.human',
    ]

    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config['hook-receiver']
        self.channel = bot.config['autojoins'][0].split(' ', 1)[0]  # may contain password
        self.lock = Lock()
        self.latest_msg = None
        logging.info("Starting hoot receiver on %s:%d",
                     self.config['host'], self.config['port'])
        asyncio.Task(asyncio.start_server(self.handle_incoming_issue,
                                          self.config['host'],
                                          self.config['port'],
                                          family=socket.AF_INET))

    def announce_issue(self, issue):
        # - url
        # - author
        # - id, name, username
        # - hattrs
        #   - category, tracker, priority, status
        # - attrs
        #   - assigned_to_id, author_id, category_id, closed_on, created_on, description, done_ratio, due_date,
        #     estimated_hours, fixed_version_id, id, is_private, lft, lock_version, parent_id, priority_id,
        #     project_id, rgt, root_id, start_date, status_id, subject, tracker_id, updated_on
        title = issue['attrs']['subject']
        if len(title) > 90:
            title = title[:90] + "…"
        msg = "\x02\x03{c}New {tracker:<10}\03\02 by \x0312{author:<13}\x03: “{title}” {url}".format(
            tracker=issue['hattrs']['tracker'],
            c=5 if issue['attrs']['tracker_id'] == 1 else 3,  # red if bug else green
            author=issue['author']['username'],
            title=title,
            url="http://redmine{}".format(issue['url']),
        )
        with self.lock:
            self.latest_msg = msg
        logging.debug("Sending message to %s: %s", self.channel, msg)
        self.bot.privmsg(self.channel, msg)

    @asyncio.coroutine
    def handle_incoming_issue(self, reader, writer):
        logging.debug("Incoming issue from %r", writer.get_extra_info('peername'))
        data = yield from reader.readline()
        try:
            data = json.loads(data.decode())
            logging.debug("Incoming issue data: %r", data)
            self.announce_issue(data)
        except ValueError:
            logging.exception("Error while decoding issue data", exc_info=True)
        finally:
            writer.close()

    @command
    def latest(self, mask, target, args):
        """
        Print latest announce again.

            %%latest
        """
        with self.lock:
            if self.latest_msg is None:
                return
            yield self.latest_msg


def main():
    config = prologin.config.load('irc-redmine-issues')
    prologin.log.setup_logging('irc-redmine-issues')

    bot_config = config['irc']
    bot_config['hook-receiver'] = config['hook-receiver']
    bot_config['includes'] = [
        'irc3.plugins.core',
        'irc3.plugins.command',
        'irc3.plugins.human',
        __name__,
    ]
    bot = irc3.IrcBot.from_config(bot_config)
    bot.run(forever=True)


if __name__ == '__main__':
    main()

