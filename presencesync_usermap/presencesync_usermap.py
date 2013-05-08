#! /usr/bin/env python3

import logging
import prologin.config
import prologin.log
import prologin.presencesync
import xml.etree.ElementTree as ET

"""Generate a map of connected contestants

The map generation uses two inputs:

    - the PresenceSync client API, to get information about connected users and
      their location
    - an single SVG pattern map of rooms

To create such a map, just draw what you want on an SVG image and put where you
want <text> objects with *exactly* two lines: the first must be the exact
machine name (e.g. "pas-r01p02") and the second can be whatever you want (it
will be replaced by the login of the connected contestants.

Look at the provided "example.svg" SVG pattern map for a fully working
example.
"""


CFG = prologin.config.load('presencesync_usermap')


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
    """
    Fill some text object according to the given `login`. If `login` is None,
    the machine is considered as not occupied.
    """

    if login is None:
        styles = DISCONNECTED_STYLES
        login = 'none'
    else:
        styles = CONNECTED_STYLES

    text[1].text = login
    for tspan, style in zip(text, styles):
        tspan.set('style', style)


def generate(logins, map_pattern, output):
    """Write the SVG user map into the `output` using the `map_pattern`
    readable file and the `logins` -> hostname mapping.
    """
    tree = ET.parse(map_pattern)
    for text in tree.getroot().iter(TEXT_TAG):
        if (
            len(text) == 2 and
            text[0].tag == TSPAN_TAG and
            text[1].tag == TSPAN_TAG
        ):
            machine_name = text[0].text
            login = logins.get(machine_name, None)
            fill_machine(text, login)

    tree.write(output, encoding='utf-8', xml_declaration=True)

def callback(logins, updates_metadata):
    logging.info('Upgrade using updates')
    try:
        with open(CFG['map_pattern'], 'rb') as map_pattern:
            with open(CFG['output'], 'wb') as output:
                generate(logins, map_pattern, output)
    except IOError as e:
        logging.exception('Cannot open files')
    except ET.ParseError as e:
        logging.exception('Cannot parse the map pattern')


if __name__ == '__main__':
    prologin.log.setup_logging('presencesync_usermap')
    prologin.presencesync.connect().poll_updates(callback)
    args = parser.parse_args()
    try:
        generate(args)
    except ET.ParseError as e:
        parser.error(str(e))
