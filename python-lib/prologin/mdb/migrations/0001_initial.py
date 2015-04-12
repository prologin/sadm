# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


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
    ]

    operations = [
        migrations.CreateModel(
            name='IPPool',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('mtype', models.CharField(choices=[('user', 'Contestant machine'), ('orga', 'Organizer machine'), ('cluster', 'Matches cluster node'), ('service', 'Server')], unique=True, verbose_name='For type', max_length=20)),
                ('network', models.CharField(unique=True, verbose_name='CIDR', max_length=32)),
                ('last', models.IntegerField(blank=True, default=0, verbose_name='Last allocation')),
            ],
            options={
                'verbose_name_plural': 'IP Pools',
                'verbose_name': 'IP Pool',
                'ordering': ('mtype',),
            },
        ),
        migrations.CreateModel(
            name='Machine',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('hostname', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[a-z0-9]*(?:\\.[a-z0-9]*)?$')], unique=True, help_text='^[a-z0-9]*(?:\\.[a-z0-9]*)?$', verbose_name='Host name', max_length=64)),
                ('aliases', models.CharField(blank=True, validators=[django.core.validators.RegexValidator(regex='^[a-z0-9]*(?:\\.[a-z0-9]*)?(?:,[a-z0-9]*(?:\\.[a-z0-9]*)?)*$')], help_text='host0,host1,etc.', max_length=512)),
                ('ip', models.GenericIPAddressField(unique=True, help_text='The IP address is automatically allocated.', verbose_name='IP')),
                ('mac', models.CharField(validators=[django.core.validators.RegexValidator(regex='[0-9a-zA-Z]{2}(?::[0-9a-zA-Z]{2}){5}')], unique=True, help_text='aa:bb:cc:dd:ee:ff', verbose_name='MAC', max_length=17)),
                ('rfs', models.IntegerField(default=0, verbose_name='RFS')),
                ('hfs', models.IntegerField(default=0, verbose_name='HFS')),
                ('mtype', models.CharField(default='orga', choices=[('user', 'Contestant machine'), ('orga', 'Organizer machine'), ('cluster', 'Matches cluster node'), ('service', 'Server')], verbose_name='Type', max_length=20)),
                ('room', models.CharField(default='other', choices=[('pasteur', 'Pasteur'), ('alt', 'Supplementary room'), ('cluster', 'Cluster'), ('other', 'Other/Unknown')], max_length=20)),
            ],
            options={
                'ordering': ('hostname', 'ip'),
            },
        ),
        migrations.CreateModel(
            name='VolatileSetting',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(verbose_name='Key', max_length=64)),
                ('value_bool', models.NullBooleanField(verbose_name='Boolean')),
                ('value_str', models.CharField(blank=True, null=True, verbose_name='String', max_length=64)),
                ('value_int', models.IntegerField(blank=True, null=True, verbose_name='Int')),
            ],
            options={
                'ordering': ('key',),
            },
        ),
        migrations.RunPython(initial_data),
    ]
