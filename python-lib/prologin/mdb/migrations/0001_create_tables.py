# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='IPPool',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('mtype', models.CharField(choices=[('user', 'Contestant machine'), ('orga', 'Organizer machine'),
                                                    ('cluster', 'Matches cluster node'), ('service', 'Server')],
                                           max_length=20, unique=True, verbose_name='For type')),
                ('network', models.CharField(max_length=32, unique=True, verbose_name='CIDR')),
                ('last', models.IntegerField(blank=True, default=0, verbose_name='Last allocation')),
            ],
            options={
                'ordering': ('mtype',),
                'verbose_name_plural': 'IP Pools',
                'verbose_name': 'IP Pool',
            },
        ),
        migrations.CreateModel(
            name='Machine',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('hostname', models.CharField(help_text='^[a-z0-9]*(?:\\.[a-z0-9]*)?$', validators=[
                    django.core.validators.RegexValidator(regex='^[a-z0-9]*(?:\\.[a-z0-9]*)?$')], max_length=64,
                                              unique=True, verbose_name='Host name')),
                ('aliases', models.CharField(help_text='host0,host1,etc.', validators=[
                    django.core.validators.RegexValidator(
                        regex='^[a-z0-9]*(?:\\.[a-z0-9]*)?(?:,[a-z0-9]*(?:\\.[a-z0-9]*)?)*$')], blank=True,
                                             max_length=512)),
                ('ip', models.GenericIPAddressField(help_text='The IP address is automatically allocated.', unique=True,
                                                    verbose_name='IP')),
                ('mac', models.CharField(help_text='aa:bb:cc:dd:ee:ff', validators=[
                    django.core.validators.RegexValidator(regex='[0-9a-zA-Z]{2}(?::[0-9a-zA-Z]{2}){5}')], max_length=17,
                                         unique=True, verbose_name='MAC')),
                ('rfs', models.IntegerField(default=0, verbose_name='RFS')),
                ('hfs', models.IntegerField(default=0, verbose_name='HFS')),
                ('mtype', models.CharField(choices=[('user', 'Contestant machine'), ('orga', 'Organizer machine'),
                                                    ('cluster', 'Matches cluster node'), ('service', 'Server')],
                                           max_length=20, default='orga', verbose_name='Type')),
                ('room', models.CharField(
                    choices=[('pasteur', 'Pasteur'), ('alt', 'Supplementary room'), ('cluster', 'Cluster'),
                             ('other', 'Other/Unknown')], max_length=20, default='other')),
            ],
            options={
                'ordering': ('hostname', 'ip'),
            },
        ),
        migrations.CreateModel(
            name='VolatileSetting',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, verbose_name='Key')),
                ('value_bool', models.NullBooleanField(verbose_name='Boolean')),
                ('value_str', models.CharField(blank=True, max_length=64, null=True, verbose_name='String')),
                ('value_int', models.IntegerField(blank=True, null=True, verbose_name='Int')),
            ],
            options={
                'ordering': ('key',),
            },
        ),
        migrations.AddField(
            model_name='machine',
            name='is_faulty',
            field=models.BooleanField(default=False, verbose_name='Faulty machine'),
        ),
        migrations.AddField(
            model_name='machine',
            name='is_faulty_details',
            field=models.TextField(blank=True, verbose_name='Details on why the machine is faulty'),
        ),
    ]
