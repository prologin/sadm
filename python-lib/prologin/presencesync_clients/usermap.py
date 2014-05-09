#! /usr/bin/env python3

import logging
import prologin.config
import prologin.log
import prologin.presencesync.client
import prologin.udb.client
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

STYLES = {
    'connected_user': (
        'font-weight: bold;',
        'fill: #208020; font-weight: bold;'
    ),
    'connected_orga': (
        'font-weight: bold;',
        'fill: #202080; font-weight: bold;'
    ),
    'connected_root': (
        'font-weight: bold;',
        'fill: #802020; font-weight: bold;'
    ),
    'disconnected': (
        'font-weight: bold;',
        'fill: #b0b0b0; font-style: italic;'
    )
}


def fill_machine(text, login=None, group=""):
    """
    Fill some text object according to the given `login`. If `login` is None,
    the machine is considered as not occupied.
    """

    if login is None:
        styles = STYLES['disconnected']
        login = 'libre'
    else:
        styles = STYLES['connected_' + group]

    text[1].text = login
    for tspan, style in zip(text, styles):
        tspan.set('style', style)


def generate(host_to_login, udb_users, map_pattern, output):
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
            login = host_to_login.get(machine_name, None)

            group = "user"  # default group
            # Search user group
            for udb_user in udb_users:
                if udb_user['login'] == login:
                    group = udb_user['group']
                    break

            fill_machine(text, login, group)

    tree.write(output, encoding='utf-8', xml_declaration=True)

def callback(logins, updates_metadata):
    host_to_login = {
        entry['hostname']: entry['login']
        for entry in logins.values()
    }
    logging.info('Upgrade using updates')
    udb_users = prologin.udb.client.connect().query()  # get all users
    try:
        with open(CFG['map_pattern'], 'rb') as map_pattern:
            with open(CFG['output'], 'wb') as output:
                generate(host_to_login, udb_users, map_pattern, output)
    except IOError as e:
        logging.exception('Cannot open files')
    except ET.ParseError as e:
        logging.exception('Cannot parse the map pattern')


if __name__ == '__main__':
    prologin.log.setup_logging('presencesync_usermap')
    prologin.presencesync.client.connect().poll_updates(callback)
    args = parser.parse_args()
    try:
        generate(args)
    except ET.ParseError as e:
        parser.error(str(e))
