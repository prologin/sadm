from django.core.management.base import BaseCommand

from prologin.mdb.models import Machine


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('hostname')

    def handle(self, *args, **options):
        Machine.objects.get(hostname=options['hostname']).delete()
