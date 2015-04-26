# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Champion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(verbose_name='nom', max_length=100)),
                ('status', models.CharField(verbose_name='statut', max_length=100, choices=[('new', 'En attente de compilation'), ('pending', 'En cours de compilation'), ('ready', 'Compilé et prêt'), ('error', 'Erreur de compilation')], default='new')),
                ('deleted', models.BooleanField(verbose_name='supprimé', default=False)),
                ('comment', models.TextField(verbose_name='commentaire')),
                ('ts', models.DateTimeField(verbose_name='date', auto_now_add=True)),
                ('author', models.ForeignKey(verbose_name='auteur', related_name='champions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'champion',
                'ordering': ['-ts'],
                'verbose_name_plural': 'champions',
            },
        ),
        migrations.CreateModel(
            name='Map',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(verbose_name='nom', max_length=100)),
                ('official', models.BooleanField(verbose_name='officielle', default=False)),
                ('ts', models.DateTimeField(verbose_name='date', auto_now_add=True)),
                ('author', models.ForeignKey(verbose_name='auteur', related_name='maps', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'carte',
                'ordering': ['-official', '-ts'],
                'verbose_name_plural': 'cartes',
            },
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('status', models.CharField(verbose_name='statut', max_length=100, choices=[('creating', 'En cours de création'), ('new', 'En attente de lancement'), ('pending', 'En cours de calcul'), ('done', 'Terminé')], default='creating')),
                ('ts', models.DateTimeField(verbose_name='date', auto_now_add=True)),
                ('options', models.CharField(verbose_name='options', max_length=500, default='{}')),
                ('file_options', models.CharField(verbose_name='file_options', max_length=500, default='{}')),
                ('author', models.ForeignKey(verbose_name='lancé par', related_name='matches', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'match',
                'ordering': ['-ts'],
                'verbose_name_plural': 'matches',
            },
        ),
        migrations.CreateModel(
            name='MatchPlayer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('score', models.IntegerField(verbose_name='score', default=0)),
                ('champion', models.ForeignKey(verbose_name='champion', to='stechec.Champion')),
                ('match', models.ForeignKey(verbose_name='match', to='stechec.Match')),
            ],
            options={
                'verbose_name': 'participant à un match',
                'ordering': ['-match'],
                'verbose_name_plural': 'participants à un match',
            },
        ),
        migrations.CreateModel(
            name='Tournament',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(verbose_name='nom', max_length=100)),
                ('ts', models.DateTimeField(verbose_name='date', auto_now_add=True)),
            ],
            options={
                'verbose_name': 'tournoi',
                'ordering': ['-ts'],
                'verbose_name_plural': 'tournois',
            },
        ),
        migrations.CreateModel(
            name='TournamentMap',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('map', models.ForeignKey(verbose_name='carte', to='stechec.Map')),
                ('tournament', models.ForeignKey(verbose_name='tournoi', to='stechec.Tournament')),
            ],
            options={
                'verbose_name': 'carte utilisée dans un tournoi',
                'ordering': ['-tournament'],
                'verbose_name_plural': 'cartes utilisées dans un tournoi',
            },
        ),
        migrations.CreateModel(
            name='TournamentPlayer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('score', models.IntegerField(verbose_name='score', default=0)),
                ('champion', models.ForeignKey(verbose_name='champion', to='stechec.Champion')),
                ('tournament', models.ForeignKey(verbose_name='tournoi', to='stechec.Tournament')),
            ],
            options={
                'verbose_name': 'participant à un tournoi',
                'ordering': ['-tournament', '-score'],
                'verbose_name_plural': 'participants à un tournoi',
            },
        ),
        migrations.AddField(
            model_name='tournament',
            name='maps',
            field=models.ManyToManyField(verbose_name='maps', through='stechec.TournamentMap', to='stechec.Map', related_name='tournaments'),
        ),
        migrations.AddField(
            model_name='tournament',
            name='players',
            field=models.ManyToManyField(verbose_name='participants', through='stechec.TournamentPlayer', to='stechec.Champion', related_name='tournaments'),
        ),
        migrations.AddField(
            model_name='match',
            name='players',
            field=models.ManyToManyField(verbose_name='participants', through='stechec.MatchPlayer', to='stechec.Champion', related_name='matches'),
        ),
        migrations.AddField(
            model_name='match',
            name='tournament',
            field=models.ForeignKey(verbose_name='tournoi', related_name='matches', null=True, blank=True, to='stechec.Tournament'),
        ),
    ]
