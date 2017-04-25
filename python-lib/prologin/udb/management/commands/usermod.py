import argparse

from django.core.management import BaseCommand

from prologin.udb.models import User

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('login')
        parser.add_argument('--ssh-pubkey-file',
                            type=argparse.FileType('r'),
                            help="set public key",
                            required=False)
        parser.add_argument('--password',
                            type=str,
                            help="set password",
                            required=False)

    def handle(self, *args, **options):
        user = User.objects.get(login=options['login'])
        if options['ssh_pubkey_file'] is not None:
            user.ssh_key = options['ssh_pubkey_file'].read().strip()
            self.stdout.write("Set public ssh key of {} to {}".format(
                user.login, user.ssh_key))
        if options['password'] is not None:
            user.password = options['password']
            self.stdout.write("Changed password of {} to {}".format(
                user.login, user.password))
        user.save()
