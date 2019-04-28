# Copyright (c) 2016 Antoine Pietri <antoine.pietri@prologin.org>
# Copyright (c) 2016 Association Prologin <info@prologin.org>
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


def check_filter_fields(fields, kwargs):
    for q in kwargs:
        base = q.split('_')[0]
        if base not in fields:
            raise ValueError('%r is not a valid query argument' % q)


def add_warning_to_django_auth_user_model_name():
    """
    Monkey-patch the default Django contrib.auth user model with a warning that
    this is not the UDB user model, as it's easy to confuse the two.
    """
    from django.contrib.auth import get_user_model
    warning = " ⚠ *not* UDB user model ⚠"
    User = get_user_model()
    User._meta.verbose_name += warning
    User._meta.verbose_name_plural += warning


def default_initial_auth_groups(apps):
    """
    Create Organizer and root groups for Django contrib.auth app.
    To be called in a Django migration.
    """
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    orga = Group.objects.create(name="Organizer")
    orga.permissions.set(Permission.objects.filter(
        codename__in=['change_user']))

    root = Group.objects.create(name="root")
    root.permissions.set(Permission.objects.all())
