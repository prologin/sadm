# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2019-02-20 10:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stechec', '0004_tournament_graphic_repartition'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournamentplayer',
            name='nb_timeout',
            field=models.IntegerField(default=0, verbose_name='nombre de timeout'),
        ),
    ]
