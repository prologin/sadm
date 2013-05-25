#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Alexandre `Zopieux` Macabies <web@zopieux.com>
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

import sys
import requests
import argparse

BASE_URL = 'http://minecraft/skin'


def handle_response(data):
    if data['ok']:
        print("Succès")
    else:
        print("Erreur : %s" % data['msg'])
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Modifie votre skin sur Prolocraft")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('skinfile', type=argparse.FileType('rb'),
        default=sys.stdin, help="Le fichier PNG de votre skin (dimensions 64x32)")
    group.add_argument('-d', '--delete', dest='delete', action='store_true',
        help="Supprimer votre skin persionnalisé (utiliser celui par défaut à la place)")

    args = parser.parse_args()

    if args.delete:
        r = requests.delete(BASE_URL).json()
        handle_response(r)

    else:
        r = requests.put(BASE_URL, files={'skin': args.skinfile})
        handle_response(r)
