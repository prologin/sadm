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
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Champion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='nom')),
                ('status', models.CharField(max_length=100, verbose_name='statut', default='new', choices=[('new', 'En attente de compilation'), ('pending', 'En cours de compilation'), ('ready', 'Compilé et prêt'), ('error', 'Erreur de compilation')])),
                ('deleted', models.BooleanField(verbose_name='supprimé', default=False)),
                ('comment', models.TextField(verbose_name='commentaire')),
                ('ts', models.DateTimeField(verbose_name='date', auto_now_add=True)),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL, verbose_name='auteur')),
            ],
            options={
                'ordering': ['-ts'],
                'verbose_name': 'champion',
                'verbose_name_plural': 'champions',
            },
        ),
        migrations.CreateModel(
            name='Map',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='nom')),
                ('official', models.BooleanField(verbose_name='officielle', default=False)),
                ('ts', models.DateTimeField(verbose_name='date', auto_now_add=True)),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL, verbose_name='auteur')),
            ],
            options={
                'ordering': ['-official', '-ts'],
                'verbose_name': 'map',
                'verbose_name_plural': 'maps',
            },
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('status', models.CharField(max_length=100, verbose_name='statut', default='creating', choices=[('creating', 'En cours de création'), ('new', 'En attente de lancement'), ('pending', 'En cours de calcul'), ('done', 'Terminé')])),
                ('ts', models.DateTimeField(verbose_name='date', auto_now_add=True)),
                ('options', models.CharField(max_length=500, verbose_name='options')),
                ('file_options', models.CharField(max_length=500, verbose_name='file_options')),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL, verbose_name='lancé par')),
            ],
            options={
                'ordering': ['-ts'],
                'verbose_name': 'match',
                'verbose_name_plural': 'matches',
            },
        ),
        migrations.CreateModel(
            name='MatchPlayer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('score', models.IntegerField(verbose_name='score', default=0)),
                ('champion', models.ForeignKey(to='stechec.Champion', verbose_name='champion')),
                ('match', models.ForeignKey(to='stechec.Match', verbose_name='match')),
            ],
            options={
                'ordering': ['-match'],
                'verbose_name': 'participant à un match',
                'verbose_name_plural': 'participants à un match',
            },
        ),
        migrations.CreateModel(
            name='Tournament',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='nom')),
                ('ts', models.DateTimeField(verbose_name='date', auto_now_add=True)),
            ],
            options={
                'ordering': ['-ts'],
                'verbose_name': 'tournoi',
                'verbose_name_plural': 'tournois',
            },
        ),
        migrations.CreateModel(
            name='TournamentMap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('map', models.ForeignKey(to='stechec.Map', verbose_name='map')),
                ('tournament', models.ForeignKey(to='stechec.Tournament', verbose_name='tournoi')),
            ],
            options={
                'ordering': ['-tournament'],
                'verbose_name': 'map utilisée dans un tournoi',
                'verbose_name_plural': 'maps utilisées dans un tournoi',
            },
        ),
        migrations.CreateModel(
            name='TournamentPlayer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('score', models.IntegerField(verbose_name='score', default=0)),
                ('champion', models.ForeignKey(to='stechec.Champion', verbose_name='champion')),
                ('tournament', models.ForeignKey(to='stechec.Tournament', verbose_name='tournoi')),
            ],
            options={
                'ordering': ['-tournament', '-score'],
                'verbose_name': 'participant à un tournoi',
                'verbose_name_plural': 'participants à un tournoi',
            },
        ),
        migrations.AddField(
            model_name='tournament',
            name='maps',
            field=models.ManyToManyField(to='stechec.Map', verbose_name='maps', through='stechec.TournamentMap'),
        ),
        migrations.AddField(
            model_name='tournament',
            name='players',
            field=models.ManyToManyField(to='stechec.Champion', verbose_name='participants', through='stechec.TournamentPlayer'),
        ),
        migrations.AddField(
            model_name='match',
            name='players',
            field=models.ManyToManyField(to='stechec.Champion', verbose_name='participants', through='stechec.MatchPlayer'),
        ),
        migrations.AddField(
            model_name='match',
            name='tournament',
            field=models.ForeignKey(verbose_name='tournoi', to='stechec.Tournament', blank=True, null=True),
        ),
        migrations.RunPython(initial_data),
    ]
