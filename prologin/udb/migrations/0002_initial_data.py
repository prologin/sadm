from django.db import migrations

from prologin.utils.django import default_initial_auth_groups


def initial_data(apps, schema_editor):
    default_initial_auth_groups(apps)


class Migration(migrations.Migration):
    dependencies = [
        ('udb', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(initial_data),
    ]
