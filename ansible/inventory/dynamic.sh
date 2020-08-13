#!/bin/bash

ssh -F inventory/ssh.cfg root@gw \
    /opt/prologin/venv/bin/python3 /var/prologin/mdb/manage.py ansible \
    || echo '{}'
