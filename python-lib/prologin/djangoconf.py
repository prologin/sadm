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

"""Utility functions to load Django configuration from external YAML files."""

import os
import os.path
import random
import sys
import yaml

# Prologin is based in France, use Europe/Paris as the default TZ if none is
# provided, and en-us as default locale (this is mostly for internal tools).
_DEFAULT_TZ = 'Europe/Paris'
_DEFAULT_LANG = 'en-us'


def use_yaml_config(path, out=None):
    """Loads configuration values from a YAML file to some dictionary.

    If the DJANGOCONF_YAML environment variable is set, use it instead of the
    provided path (used when debugging for example).

    If no dictionary is provided, frame magic is done in order to get the
    globals of our caller (most likely the globals of settings.py).

    Args:
      path: Path to the YAML configuration file.
      out: Dictionary where to store the loaded Django settings.

    Returns:
      The parsed YAML file so that the settings file can load more custom
      settings if wanted.
    """
    path = os.environ.get('DJANGOCONF_YAML', path)
    if not os.path.exists(path):
        raise RuntimeError("No YAML configuration file at %r. Please "
                           "configure the application." % path)
    with open(path) as fp:
        cfg = yaml.load(fp)

    if out is None:
        try:
            out = sys._getframe().f_back.f_globals
        except AttributeError:
            raise RuntimeError("Unable to automagically get the globals "
                               "dictionary, use the 'out' argument.")

    _load_config(cfg, out)
    return cfg


def _load_config(cfg, out):
    """Loads the configuration values to the out dict."""

    # Mandatory
    out['SECRET_KEY'] = cfg.get('secret_key')
    out['DATABASES'] = cfg.get('db')

    # Optional with sane defaults
    out['DEBUG'] = out['TEMPLATE_DEBUG'] = cfg.get('debug', False)
    out['TIME_ZONE'] = cfg.get('tz', _DEFAULT_TZ)
    out['LANGUAGE_CODE'] = cfg.get('lang', _DEFAULT_LANG)
