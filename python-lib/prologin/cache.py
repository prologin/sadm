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

"""A simple caching module to avoid recomputing some expensive values for a
certain amount of time.

@prologin.cache.for_(<seconds>)
def my_func():
    ...

Does not work with kwargs (TODO: add frozendict).
"""

import functools
import time

def for_(seconds):
    def decorator(func):
        cache = {}
        @functools.wraps(func)
        def wrapper(*args):
            if args in cache:
                ts, val = cache[args]
                if ts + seconds >= time.time():
                    return val
                else:
                    del cache[args]
            val = func(*args)
            cache[args] = (time.time(), val)
            return val
        return wrapper
    return decorator
