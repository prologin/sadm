# -*- encoding: utf-8 -*-
# This file is part of Prologin-SADM.
#
# Copyright (c) 2013-2015 Antoine Pietri <antoine.pietri@prologin.org>
# Copyright (c) 2011 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2011 Association Prologin <info@prologin.org>
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

import asyncio
import optparse
import prologin.config
import prologin.log
import tornado.platform.asyncio

from .monitoring import monitoring_start
from .master import MasterNode

if __name__ == '__main__':
    # Argument parsing
    parser = optparse.OptionParser()
    parser.add_option('-l', '--local-logging', action='store_true',
                      dest='local_logging', default=False,
                      help='Activate logging to stdout.')
    parser.add_option('-v', '--verbose', action='store_true',
                      dest='verbose', default=False,
                      help='Verbose mode.')
    options, args = parser.parse_args()

    # Use the asyncio backend for tornado
    tornado.platform.asyncio.AsyncIOMainLoop().install()

    # Logging
    prologin.log.setup_logging('masternode', verbose=options.verbose,
                               local=options.local_logging)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    # Config
    config = prologin.config.load('masternode')

    # RPC Service
    s = MasterNode(config=config, app_name='masternode',
                   secret=config['master']['shared_secret'].encode('utf-8'))
    s.listen(config['master']['port'])

    # Monitoring
    masternode_tasks.set_function(lambda: len(s.worker_tasks))
    masternode_workers.set_function(lambda: len(s.workers))
    monitoring_start()

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass
