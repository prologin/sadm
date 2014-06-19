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

setup(name='ProloginSADM',
      version='1.0',
      description='Utility libraries for Prologin Python services',
      author='Pierre Bourdon',
      author_email='pierre.bourdon@prologin.org',
      url='http://bitbucket.org/prologin/sadm/',
      packages=find_packages(),
      scripts=['prologin/workernode/compile-champion.sh',
               'prologin/rpc/prolorpc',
               'prologin/set_hostname.py',
               ],
      package_data={
          'prologin.concours': ['stechec/static/**/*.*',
                                'stechec/templates/*'],
          'prologin.homepage': ['static/*', 'templates/*'],
          'prologin.minecraft': ['static/*.png',
                                 'static/bin/*.jar',
                                 'static/bin/md5s',
                                 'static/bin/natives/*'],
          'prologin.hfs': ['create_nbd.sh'],
      },
      test_suite='nose.collector',
     )
