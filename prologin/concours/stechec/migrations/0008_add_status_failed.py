# Generated by Django 2.2.10 on 2020-03-07 17:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stechec', '0007_matchplayer_has_timeout'),
    ]

    operations = [
        migrations.AlterField(
            model_name='match',
            name='status',
            field=models.CharField(
                choices=[
                    ('creating', 'En cours de création'),
                    ('new', 'En attente de lancement'),
                    ('pending', 'En cours de calcul'),
                    ('done', 'Terminé'),
                    ('failed', 'Échec'),
                ],
                default='creating',
                max_length=100,
                verbose_name='statut',
            ),
        ),
        migrations.AlterField(
            model_name='champion',
            name='status',
            field=models.CharField(
                choices=[
                    ('new', 'En attente de compilation'),
                    ('pending', 'En cours de compilation'),
                    ('ready', 'Compilé et prêt'),
                    ('error', 'Erreur de compilation'),
                    ('failed', 'Compilation abandonnée'),
                ],
                default='new',
                max_length=100,
                verbose_name='statut',
            ),
        ),
    ]