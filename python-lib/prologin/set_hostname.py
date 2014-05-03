#!/usr/bin/env python
# encoding: utf-8

import subprocess

def set_hostname():
    """Get and set this machine hostname from gw dns server."""
    out = subprocess.check_output('ip addr', shell=True).decode().splitlines()

    # Get this machine public IP addr
    ip_line = [line for line in out if 'inet ' in line and '127.0.0.1' not in line]
    assert len(ip_line) == 1, \
        "More than one public IP addr: {}".format(ip_line)

    ip = ip_line[0].split()[1].split('/')[0]

    # Get this machine hostname
    fqdn_hostname = subprocess.check_output('dig +short -x {}'.format(ip),
                                       shell=True).decode()

    hostname = fqdn_hostname.split('.')[0]

    # Set his machine hostname
    subprocess.call('hostnamectl set-hostname {}.prolo'.format(hostname), shell=True)

if __name__ == '__main__':
    set_hostname()
