from django.core.management.base import BaseCommand

from prologin.concours.stechec.models import Match, Champion


class Command(BaseCommand):
    help = "Restart failed masternode tasks"

    def handle(self, *args, **options):
        Champion.objects.filter(status='failed').update(status='new')
        Match.objects.filter(status='failed').update(status='new')
