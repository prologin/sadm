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

"""Common configuration loading logic for libraries."""

import os
import os.path
import yaml

DEFAULT_CFG_DIR = '/etc/prologin'
LOADED_CONFIGS = {}


class ConfigReadError(Exception):
    pass


def load(profile):
    """Load (if needed) and return the configuration file for `profile`.

    Profile configurations are cached. Look for configuration profiles in the
    "CFG_DIR" environment variable if it is set, or in the DEFAULT_CFG_DIR
    otherwise. Raise a ConfigReadError if no such file exist.
    """

    try:
        return LOADED_CONFIGS[profile]
    except KeyError:
        pass

    cfg_filename = '{}.yml'.format(profile)
    cfg_directory = os.environ.get('CFG_DIR', DEFAULT_CFG_DIR)
    cfg_path = os.path.join(cfg_directory, cfg_filename)

    try:
        with open(cfg_path, 'r') as cfg_fp:
            cfg = yaml.safe_load(cfg_fp)
    except IOError:
        raise ConfigReadError("%s does not exist (specify CFG_DIR?)"
                              % cfg_path)

    LOADED_CONFIGS[profile] = cfg

    return cfg
