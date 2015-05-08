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

import ipaddress

from django.core.validators import RegexValidator
from django.db import models

from django_prometheus.models import ExportModelOperationsMixin


class Machine(ExportModelOperationsMixin('machine'), models.Model):
    TYPES = (
        ('user', 'Contestant machine'),
        ('orga', 'Organizer machine'),
        ('cluster', 'Matches cluster node'),
        ('service', 'Server'),
    )

    ROOMS = (
        ('pasteur', 'Pasteur'),
        ('alt', 'Supplementary room'),
        ('cluster', 'Cluster'),
        ('other', 'Other/Unknown'),
    )

    # Vaguely inaccurate, KISS.
    HOSTNAME_REGEX = r'^[a-z0-9-]*(?:\.[a-z0-9]*)?$'
    ALIASES_REGEX = r'^{0}(?:,{0})*$'.format(HOSTNAME_REGEX[1:-1])
    MAC_REGEX = r'[0-9a-zA-Z]{2}(?::[0-9a-zA-Z]{2}){5}'

    hostname = models.CharField(max_length=64, unique=True,
                                verbose_name='Host name',
                                validators=[RegexValidator(regex=HOSTNAME_REGEX)],
                                help_text=HOSTNAME_REGEX)
    aliases = models.CharField(max_length=512, blank=True,
                               validators=[RegexValidator(regex=ALIASES_REGEX)],
                               help_text='host0,host1,etc.')
    ip = models.GenericIPAddressField(unique=True, verbose_name='IP',
                                      help_text='The IP address is automatically allocated.')
    mac = models.CharField(max_length=17, unique=True, verbose_name='MAC',
                           validators=[RegexValidator(regex=MAC_REGEX)],
                           help_text='aa:bb:cc:dd:ee:ff')
    rfs = models.IntegerField(verbose_name='RFS', default=0)
    hfs = models.IntegerField(verbose_name='HFS', default=0)
    mtype = models.CharField(max_length=20, choices=TYPES, verbose_name='Type',
                             default='orga')
    room = models.CharField(max_length=20, choices=ROOMS, default='other')
    is_faulty = models.BooleanField(default=False, verbose_name="Faulty machine")
    is_faulty_details = models.TextField(blank=True, verbose_name="Details on why the machine is faulty")

    def __str__(self):
        return self.hostname

    def save(self, *args, **kwargs):
        if not self.ip:
            self.allocate_ip()
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'hostname': self.hostname,
            'aliases': self.aliases,
            'ip': self.ip,
            'mac': self.mac,
            'rfs': self.rfs,
            'hfs': self.hfs,
            'mtype': self.mtype,
            'room': self.room,
            'is_faulty': self.is_faulty,
        }

    def allocate_ip(self):
        if self.mtype == 'orga':
            pooltype = 'user'  # organizers are in the same pool as users
        else:
            pooltype = self.mtype
        pool = IPPool.objects.get(mtype=pooltype)
        pool.last += 1
        pool.save()

        net = ipaddress.IPv4Network(pool.network)
        self.ip = str(net.network_address + pool.last)

    class Meta:
        ordering = ('hostname', 'ip')


class IPPool(ExportModelOperationsMixin('ippool'), models.Model):
    mtype = models.CharField(max_length=20, choices=Machine.TYPES, unique=True,
                             verbose_name='For type')
    network = models.CharField(max_length=32, unique=True, verbose_name='CIDR')
    last = models.IntegerField(blank=True, default=0,
                               verbose_name='Last allocation')

    def __str__(self):
        return 'Pool for %r: %s' % (self.mtype, self.network)

    class Meta:
        ordering = ('mtype',)
        verbose_name = 'IP Pool'
        verbose_name_plural = 'IP Pools'


class VolatileSetting(ExportModelOperationsMixin('volatile'), models.Model):
    key = models.CharField(max_length=64, verbose_name='Key')
    value_bool = models.NullBooleanField(verbose_name='Boolean')
    value_str = models.CharField(max_length=64, null=True, blank=True,
                                 verbose_name='String')
    value_int = models.IntegerField(null=True, blank=True, verbose_name='Int')

    def __str__(self):
        return self.key

    class Meta:
        ordering = ('key',)


# Import the signal receivers so they are activated
import prologin.mdb.receivers
