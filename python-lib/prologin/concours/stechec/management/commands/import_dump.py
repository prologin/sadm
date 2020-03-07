import argparse
import gzip
import shutil
import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from prologin.concours.stechec.models import Match


class Command(BaseCommand):
    help = "Create a dummy match that uses the specified JSON dump, for testing purposes"

    def add_arguments(self, parser):
        parser.add_argument('dump', type=argparse.FileType('rb'))

    def handle(self, *args, **options):
        user = get_user_model().objects.first()
        if user is None:
            self.stderr.write(
                "No user found. Create a dummy user (eg. manage.py createsuperuser) "
                "before running this command."
            )
            sys.exit(1)

        match = Match(author=user, status='done')

        with transaction.atomic():
            match.save()
            match.refresh_from_db()
            path = match.dump_path
            path.parent.mkdir(parents=True, exist_ok=True)

            with gzip.open(str(path), 'w') as gzipped:
                shutil.copyfileobj(options['dump'], gzipped)

        self.stdout.write("Match created with ID: {}".format(match.pk))
        self.stdout.write("        Dump saved at: {}".format(path))
        self.stdout.write(
            "    Match detail page: http://127.0.0.1:8000{}".format(
                match.get_absolute_url()
            )
        )
