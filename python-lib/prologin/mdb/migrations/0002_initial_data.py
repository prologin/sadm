# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def initial_data(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    IPPool = apps.get_model('mdb', 'IPPool')
    Permission = apps.get_model('auth', 'Permission')
    VolatileSetting = apps.get_model('mdb', 'VolatileSetting')

    IPPool(last=0, mtype="user", network="192.168.0.0/24", pk=1).save()
    IPPool(last=0, mtype="cluster", network="192.168.2.0/24", pk=2).save()
    IPPool(last=0, mtype="service", network="192.168.1.0/24", pk=3).save()

    VolatileSetting(key="allow_self_registration",
                    value_bool=True,
                    pk=1).save()

    g = Group(name="Organizer", pk=1)
    g.save()

    g.permissions = Permission.objects.filter(codename__in=['change_user'])
    g = Group(name="root", pk=1)
    g.save()
    g.permissions = Permission.objects.all()


class Migration(migrations.Migration):
    dependencies = [
        ('mdb', '0001_create_tables'),
    ]

    operations = [
        migrations.RunPython(initial_data),
    ]
