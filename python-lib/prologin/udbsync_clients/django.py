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

import django
import functools
import logging
import os
import prologin.config
import prologin.log
import prologin.udbsync.client
import sys


def sync_groups(cfg, uobj, data):
    from django.contrib.auth import models as auth_models
    groups = []
    for ty in ('user', 'orga', 'root'):
        cfg_key = '%s_group' % ty
        if cfg.get(cfg_key, '') and data['group'] == ty:
            groups.append(auth_models.Group.objects.get(name=cfg[cfg_key]))
    uobj.groups.clear()
    uobj.groups.add(*groups)

    uobj.is_staff = data['group'] in cfg.get('staff_groups', [])
    uobj.is_superuser = data['group'] in cfg.get('superuser_groups', [])


def callback(cfg, users, updates_metadata):
    # Django is imported from there because DJANGO_SETTINGS_MODULE needs to be
    # configured.
    from django.contrib.auth import get_user_model

    UserModel = get_user_model()  # noqa

    logging.info("Got events: %r", updates_metadata)
    for login, status in updates_metadata.items():
        if status in ('created', 'updated'):
            try:
                u = UserModel.objects.get(username=login)
            except UserModel.DoesNotExist:
                u = UserModel.objects.create_user(login,
                                                  email='%s@devnull' % login,
                                                  password=users[login]['password'])
            u.first_name = users[login]['firstname']
            u.last_name = users[login]['lastname']
            u.set_password(users[login]['password'])
            u.is_active = users[login]['group'] in cfg.get('allowed_groups', '')
            sync_groups(cfg, u, users[login])
            u.save()

        if status == 'deleted':
            try:
                u = UserModel.objects.get(username=login)
            except UserModel.DoesNotExist:
                logging.warning("Ignoring deletion of user %r", login)
                continue
            u.is_active = False
            u.save()


if __name__ == '__main__':
    try:
        app_name = sys.argv[1]
    except IndexError:
        print("Usage: %s <app name>" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    prologin.log.setup_logging('udbsync_django.%s' % app_name)
    cfg = prologin.config.load('%s-udbsync' % app_name)
    sys.path.insert(0, '.')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'prologin.%s.settings' % app_name
    django.setup()
    callback = functools.partial(callback, cfg)
    prologin.udbsync.client.connect().poll_updates(callback)
