# SPDX-License-Identifier: GPL-2.0-or-later
import logging
import optparse
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prologin.concours.settings")

import django

django.setup()

import prologin.config
import prologin.log

from .matchmaker import MatchMaker
from .monitoring import monitoring_start

if __name__ == "__main__":
    # Argument parsing
    parser = optparse.OptionParser()
    parser.add_option(
        "-l",
        "--local-logging",
        action="store_true",
        dest="local_logging",
        default=False,
        help="Activate logging to stdout.",
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        default=False,
        help="Verbose mode.",
    )
    options, args = parser.parse_args()

    # Config
    config = prologin.config.load("matchmaker")

    # RPC Service
    s = MatchMaker(
        config=config,
        app_name="matchmaker",
        secret=config["matchmaker"]["shared_secret"].encode("utf-8"),
    )

    # Logging
    prologin.log.setup_logging(
        "matchmaker", verbose=options.verbose, local=options.local_logging
    )
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.server").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.web").setLevel(logging.WARNING)

    # Monitoring
    monitoring_start()

    try:
        s.run()
    except KeyboardInterrupt:
        pass
