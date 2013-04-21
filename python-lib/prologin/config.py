# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Pierre-Marie de Rodat <pmderodat@kawie.fr>
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

"""Common configuration loading logics for libraries."""

import os
import os.path
import yaml

class NoConfigDir(Exception):
    pass

class ConfigReadError(Exception):
    pass

loaded_configs = {}

def load(profile):
    """Load (if needed) and return the configuration file for `profile`.

    Profile configurations are cached. Raise a NoConfigDir if the "CFG_DIR"
    environment variable is not set, and raise a ConfigReadError if no such
    file exist.
    """

    try:
        return loaded_configs[profile]
    except KeyError:
        pass

    cfg_filename = '{}.yml'.format(profile)

    try:
        cfg_directory = os.environ['CFG_DIR']
    except KeyError:
        raise NoConfigDir()

    cfg_path = os.path.join(cfg_directory, cfg_filename)

    try:
        with open(cfg_path, 'r') as cfg_fp:
            cfg = yaml.load(cfg_fp)
    except IOError:
        raise ConfigReadError(cfg_path)

    loaded_configs[profile] = cfg

    return cfg
