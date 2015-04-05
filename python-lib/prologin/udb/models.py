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


class User(models.Model):
    TYPES = (
        ('user', 'Contestant'),
        ('orga', 'Organizer'),
        ('root', 'root'),
    )

    login = models.CharField(max_length=64, unique=True, db_index=True)
    firstname = models.CharField(max_length=64, verbose_name='First name')
    lastname = models.CharField(max_length=64, verbose_name='Last name')
    uid = models.IntegerField(unique=True, db_index=True, verbose_name='UID')
    group = models.CharField(max_length=20, choices=TYPES)
    password = models.CharField(max_length=64, help_text='pwgen -cnB 8')
    shell = models.CharField(max_length=64, default='/bin/bash')
    ssh_key = models.CharField(max_length=4096, null=True, blank=True,
                               verbose_name='SSH public key')

    @property
    def realname(self):
        return self.firstname + ' ' + self.lastname

    def __str__(self):
        return self.login

    def to_dict(self):
        return {
            'login': self.login,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'uid': self.uid,
            'group': self.group,
            'password': self.password,
            'shell': self.shell,
            'ssh_key': self.ssh_key,
        }

    class Meta:
        ordering = ('group', 'login',)


# Import the signal receivers so they are activated
import prologin.udb.receivers
