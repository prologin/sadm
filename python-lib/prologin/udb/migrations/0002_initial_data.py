# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def initial_data(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    orga = Group.objects.create(name="orga")
    orga.permissions.set(Permission.objects.filter(codename__in=['change_user']))

    root = Group.objects.create(name="root")
    root.permissions.set(Permission.objects.all())


class Migration(migrations.Migration):
    dependencies = [
        ('udb', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(initial_data),
    ]
