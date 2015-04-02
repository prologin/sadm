#!/usr/bin/env python
# encoding: utf-8

import subprocess


def set_hostname():
    """Gets and sets this machine hostname using reverse DNS."""

    # Get this machine public IP addr
    out = subprocess.check_output(['/usr/bin/ip', 'addr']).decode().splitlines()
    ip_line = [line for line in out if 'inet ' in line and '127.0.0.1' not in line]
    assert len(ip_line) == 1, \
        "More than one public IP addr: {}".format(ip_line)

    ip = ip_line[0].split()[1].split('/')[0]

    # Get this machine hostname
    fqdn_hostname = subprocess.check_output(['/usr/bin/dig', '+short', '-x', ip]).decode()

    assert fqdn_hostname, \
        "Reverse DNS is not working! Check your DNS settings!"

    hostname = fqdn_hostname.split('.')[0]

    # Set this machine hostname
    subprocess.call(['/usr/bin/hostnamectl', 'set-hostname', '{}.prolo'.format(hostname)])


if __name__ == '__main__':
    set_hostname()
