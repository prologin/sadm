#! /usr/bin/env python
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

from setuptools import setup, find_packages

setup(
    name='ProloginSADM',
    version='1.0',
    description='Utility libraries for Prologin Python services',
    author='Association Prologin',
    author_email='info@prologin.org',
    url='https://github.com/prologin/sadm/',
    packages=find_packages(),
    scripts=['prologin/rpc/prolorpc', 'prologin/xhack.py',],
    package_data={
        'prologin.concours': [
            'stechec/static/**/*.*',
            'stechec/templates/**/*',
        ],
        'prologin.hfs': ['create_nbd.sh'],
        'prologin.homepage': ['static/*', 'templates/*'],
        'prologin.netboot': ['script.ipxe'],
        'prologin.workernode': ['compile-champion.sh'],
    },
    test_suite='nose.collector',
    zip_safe=False,
)
