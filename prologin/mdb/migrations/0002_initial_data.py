from django.db import migrations

from prologin.utils.django import default_initial_auth_groups


def initial_data(apps, schema_editor):
    default_initial_auth_groups(apps)

    IPPool = apps.get_model('mdb', 'IPPool')
    VolatileSetting = apps.get_model('mdb', 'VolatileSetting')

    IPPool.objects.create(last=0, mtype="user", network="192.168.0.0/24")
    IPPool.objects.create(last=0, mtype="cluster", network="192.168.2.0/24")
    IPPool.objects.create(last=0, mtype="service", network="192.168.1.0/24")

    VolatileSetting.objects.create(
        key="allow_self_registration", value_bool=True
    )


class Migration(migrations.Migration):
    dependencies = [
        ('mdb', '0001_create_tables'),
    ]

    operations = [
        migrations.RunPython(initial_data),
    ]
