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

import re
import string
import subprocess
import unicodedata

from django.core.management import BaseCommand, CommandError
from optparse import make_option
from prologin.udb.models import User


def make_ascii(s):
    s = unicodedata.normalize('NFKD', s)
    return s.encode('ascii', 'ignore').decode('utf-8').lower()


def generate_password(length):
    proc = subprocess.Popen(['pwgen', '-cnB', str(length)],
                            stdout=subprocess.PIPE)
    out, err = proc.communicate()
    return out.strip().decode('utf-8')


def create_users(names, options):
    uid = options['uidbase']
    logins = set()  # To check for duplicates
    for row in names:
        if options['passwords']:
            t, passw = row.split(':')
        else:
            t = row
        if options['logins']:
            login = make_ascii(t)
            firstname = login
            lastname = login
        else:
            firstname, lastname = t
            fn, ln = make_ascii(firstname), make_ascii(lastname)

            parts = re.split('[^a-z]', fn)
            login = ''.join(p.strip()[0] for p in parts if p.strip())

            ln = ''.join(c for c in ln if c in string.ascii_lowercase)
            ln = ln[:10]
            login += ln

            base_login = login
            i = 1
            while login in logins:
                login = base_login + str(i)
                i += 1

        logins.add(login)

        u = User()
        u.login = login
        u.firstname = firstname.title()
        u.lastname = lastname.title()
        u.uid = uid
        u.group = options['type']

        if options['passwords']:
            u.password = passw
        else:
            u.password = generate_password(options['pwdlen'])

        print("Adding user %s (login: %s)" % (u.realname, u.login))

        u.save()
        uid += 1



class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--file', help='File with "first name\\tlast name" lines'),
        make_option('--type', default='user', help='User type (user/orga/root)'),
        make_option('--pwdlen', type='int', default=8, help='Password length'),
        make_option('--uidbase', type='int', default=10000, help='Base UID'),
        make_option('--logins', action='store_true', default=False, help='File contains logins, not real names'),
        make_option('--passwords', action='store_true', default=False, help='File contains passwords after a colon'),
    )

    def handle(self, *args, **options):
        if options['file'] is None:
            raise CommandError('Missing --file')
        names = []
        with open(options['file']) as fp:
            lines = [l for l in fp.read().split('\n') if l]
            for l in lines:
                if options['logins']:
                    names.append(l.strip())
                else:
                    firstname, lastname = [f.strip() for f in l.split('\t')]
                    names.append((firstname, lastname))

        create_users(names, options)
