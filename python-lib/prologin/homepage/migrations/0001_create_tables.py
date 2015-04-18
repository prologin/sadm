# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(max_length=64)),
                ('url', models.CharField(max_length=128)),
                ('contest_only', models.BooleanField(verbose_name='Contest restricted')),
                ('display_order', models.IntegerField()),
            ],
            options={
                'ordering': ('display_order', 'name'),
            },
        ),
    ]
