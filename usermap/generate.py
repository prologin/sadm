#! /usr/bin/env python3

import argparse
import prologin.udb
import sys
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Generate a map of connected contestants',
    epilog='''The map generation uses two inputs:

    - the MDB/UDB APIs, to get information about connected users and their
      location
    - an SVG pattern map of rooms

To create such a map, just draw what you want on an SVG image and put where you
want <text> objects with *exactly* two lines: the first must be the exact
machine name (e.g. "pas-r01p02") and the second can be whatever you want (it
will be replaced by the login of the connected contestants.

Look at the provided "example.svg" SVG pattern map for a fully working
example.'''
)
parser.add_argument(
    'map', type=argparse.FileType('rb'),
    help='Map to fill with contestant logins'
)
parser.add_argument(
    '-o', dest='output', type=argparse.FileType('wb'),
    default=open(sys.stdout.fileno(), 'wb'),
    help='Output file'
)


TEXT_TAG = '{http://www.w3.org/2000/svg}text'
TSPAN_TAG = '{http://www.w3.org/2000/svg}tspan'

# CSS style for location labels: first line is for the machine name line,
# second one is for the login line.

CONNECTED_STYLES = (
    'font-weight: bold;',
    'fill: #208020; font-weight: bold;'
)
DISCONNECTED_STYLES = (
    'font-weight: bold;',
    'fill: #b0b0b0; font-style: italic;'
)


def fill_machine(text, login=None):
    '''
    Fill some text object according to the given `login`. If `login` is None,
    the machine is considered as not occupied.
    '''

    if login is None:
        styles = DISCONNECTED_STYLES
        login = 'none'
    else:
        styles = CONNECTED_STYLES

    text[1].text = login
    for tspan, style in zip(text, styles):
        tspan.set('style', style)


def generate(args):

    logins = {
        user['curr_machine']: user['login'],
        for user in prologin.udb.query()
    }

    tree = ET.parse(args.map)
    for text in tree.getroot().iter(TEXT_TAG):
        if (
            len(text) == 2 and
            text[0].tag == TSPAN_TAG and
            text[1].tag == TSPAN_TAG
        ):
            machine_name = text[0].text
            login = logins.get(machine_name, None)
            fill_machine(text, login)

    tree.write(args.output, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        generate(args)
    except ET.ParseError as e:
        parser.error(str(e))
