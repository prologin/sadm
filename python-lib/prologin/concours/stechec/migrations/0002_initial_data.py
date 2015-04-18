# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


def initial_data(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    g = Group(name="Organizer", pk=1)
    g.save()
    g.permissions = Permission.objects.filter(codename__in=['change_user'])

    g = Group(name="root", pk=2)
    g.save()
    g.permissions = Permission.objects.all()


class Migration(migrations.Migration):
    dependencies = [
        ('stechec', '0001_create_tables'),
    ]

    operations = [
        migrations.RunPython(initial_data),
    ]
