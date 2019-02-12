import argparse
import prologin.concours.stechec.models as models
from django.contrib.auth.models import User
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Import a champion from a tarball"

    def add_arguments(self, parser):
        parser.add_argument('import_file', type=argparse.FileType('rb'))
        parser.add_argument('champion_name', type=str)

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='auto-import')
        except User.DoesNotExist:
            user = User(username='auto-import')
            user.save()

        champion = models.Champion(
            name = options['champion_name'],
            author = user,
            status = 'new',
            comment = 'Manually imported champion')
        champion.save()
        champion.sources = options['import_file'].read()

