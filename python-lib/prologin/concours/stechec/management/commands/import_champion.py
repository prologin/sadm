import argparse
import prologin.concours.stechec.models as models
from django.contrib.auth.models import User
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Import a champion from a tarball"

    def add_arguments(self, parser):
        parser.add_argument('import_file', type=argparse.FileType('rb'))
        parser.add_argument('user_id', type=int)

    def handle(self, *args, **options):
        try:
            user = User.objects.get(pk=options['user_id'])
        except User.DoesNotExist:
            user = User(pk=options['user_id'],
                username='autoimport-{}'.format(options['user_id']))
            user.save()

        champion = models.Champion(
            name = 'autoimport-{}'.format(options['user_id']),
            author = user,
            status = 'new',
            comment = 'Manually imported champion')
        champion.save()
        champion.sources = options['import_file'].read()

