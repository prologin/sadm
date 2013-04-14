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

from django.db import models


class Machine(models.Model):
    TYPES = (
        ('user', 'Contestant machine'),
        ('orga', 'Organizer machine'),
        ('cluster', 'Matches cluster node'),
        ('service', 'Server'),
    )

    ROOMS = (
        ('pasteur', 'Pasteur'),
        ('masters', 'Masters'),
        ('cluster', 'Cluster (LSE)'),
        ('other', 'Other/Unknown'),
    )

    hostname = models.CharField(max_length=64, unique=True,
                                verbose_name='Host name')
    aliases = models.CharField(max_length=512, blank=True)
    ip = models.IPAddressField(unique=True, verbose_name='IP')
    mac = models.CharField(max_length=17, unique=True, verbose_name='MAC')
    rfs = models.IntegerField(verbose_name='RFS')
    hfs = models.IntegerField(verbose_name='HFS')
    mtype = models.CharField(max_length=20, choices=TYPES, verbose_name='Type')
    room = models.CharField(max_length=20, choices=ROOMS)

    def __str__(self):
        return self.hostname

    class Meta:
        ordering = ('hostname', 'ip')


class VolatileSetting(models.Model):
    key = models.CharField(max_length=64, verbose_name='Key')
    value_bool = models.NullBooleanField(verbose_name='Boolean')
    value_str = models.CharField(max_length=64, null=True, blank=True,
                                 verbose_name='String')
    value_int = models.IntegerField(null=True, blank=True, verbose_name='Int')

    def __str__(self):
        return self.key

    class Meta:
        ordering = ('key',)
