#!/usr/bin/env python
# encoding: utf-8

import subprocess

def set_hostname():
    """Get and set this machine hostname from gw dns server."""
    out = subprocess.check_output('ip addr')

    # Get this machine public IP addr
    ip_line = [line for line in out if 'inet ' in line and '127.0.0.1' not in line]
    assert len(ip_line) == 1, \
        "More than one public IP addr: {}".format(ip_line)

    # Get this machine hostname
    hostname = subprocess.check_output('dig -x +short {}'.format(machine_ip))

    # Set his machine hostname
    subprocess.call('hostnamectl set-hostname {}'.format(hostname))

if __name__ == '__main__':
    set_hostname()
