# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2013 Association Prologin <info@prologin.org>
#
# Prologin-SADM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prologin-SADM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prologin-SADM.  If not, see <http://www.gnu.org/licenses/>.

# Exports the data required to print password sheets for users.

from django.core.management import BaseCommand, CommandError
from prologin.udb.models import User


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--type', default='user',
                            help='User type (user/orga/root)')

    def handle(self, *args, **options):
        users = User.objects.filter(group=options['type'])
        for u in users:
            print("%s\t%s\t%s" % (u.realname, u.login, u.password))
