# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2013 Association Prologin <info@prologin.org>
#
# Prologin-SADM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prologin-SADM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prologin-SADM.  If not, see <http://www.gnu.org/licenses/>.

import os

import logging
import logging.handlers


# Do not log to stderr if started by systemd
LOG_STDERR = os.getppid() != 1


def setup_logging(program, verbose=False, local=LOG_STDERR):
    """Sets up the default Python logger.

    Always log to syslog, optionaly log to stdout.

    Args:
      program: Name of the program logging informations.
      verbose: If true, log more messages (DEBUG instead of INFO).
      local: If true, log to stderr as well as syslog.
    """
    loggers = []
    loggers.append(logging.handlers.SysLogHandler('/dev/log'))
    if local:
        loggers.append(logging.StreamHandler())
    for logger in loggers:
        logger.setFormatter(logging.Formatter(
            program + ': [%(levelname)s] %(message)s'
        ))
        logging.getLogger('').addHandler(logger)
    logging.getLogger('').setLevel(logging.DEBUG if verbose else logging.INFO)
