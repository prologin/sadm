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

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F
import pwd

from django_prometheus.models import ExportModelOperationsMixin

import prologin.utils.django


def validate_unix_uid(login: str):
    """Ensures 'login' does not already exist as a system-managed uid."""
    try:
        uid: int = pwd.getpwnam(login).pw_uid
    except KeyError:
        return
    # https://en.wikipedia.org/wiki/User_identifier#Reserved_ranges
    if 0 <= uid < 1000 or 60000 <= uid <= 65533:
        raise ValidationError(
            f"Username {login} is associated with uid {uid}, which is likely a system-managed user."
        )


class User(ExportModelOperationsMixin('user'), models.Model):
    TYPES = (
        ('user', 'Contestant'),
        ('orga', 'Organizer'),
        ('root', 'root'),
    )

    LOGIN_REGEX = r'^([a-z_][a-z0-9_]{0,30})$'

    login = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        validators=[RegexValidator(regex=LOGIN_REGEX)],
    )
    firstname = models.CharField(max_length=64, verbose_name='First name')
    lastname = models.CharField(max_length=64, verbose_name='Last name')
    uid = models.IntegerField(unique=True, db_index=True, verbose_name='UID')
    group = models.CharField(max_length=20, choices=TYPES)
    password = models.CharField(max_length=64, help_text='pwgen -cnB 8')
    shell = models.CharField(max_length=64, default='/bin/bash')
    ssh_key = models.CharField(
        max_length=4096, null=True, blank=True, verbose_name='SSH public key'
    )

    @property
    def realname(self):
        return '{} {}'.format(self.firstname, self.lastname)

    def __str__(self):
        return self.login

    def save(self, *args, **kwargs):
        validate_unix_uid(self.login)
        if not self.uid:
            self.allocate_uid()
        super().save(*args, **kwargs)

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
            'id': self.pk,
        }

    def allocate_uid(self):
        pool = UIDPool.objects.get(group=self.group)
        pool.last = F('last') + 1  # Atomic increment
        pool.save()
        pool.refresh_from_db()
        self.uid = pool.base + pool.last

    class Meta:
        ordering = (
            'group',
            'login',
        )


class UIDPool(ExportModelOperationsMixin('uidpool'), models.Model):
    group = models.CharField(
        max_length=20, choices=User.TYPES, unique=True, verbose_name='For type'
    )
    base = models.IntegerField(unique=True, verbose_name='Base UID')
    last = models.IntegerField(
        blank=True, default=0, verbose_name='Last allocation'
    )

    def __str__(self):
        return 'Pool for %r' % self.group

    class Meta:
        ordering = ('group',)
        verbose_name = 'UID Pool'
        verbose_name_plural = 'UID Pools'


prologin.utils.django.add_warning_to_django_auth_user_model_name()

# Import the signal receivers so they are activated
import prologin.udb.receivers
