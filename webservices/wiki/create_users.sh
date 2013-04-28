#!/usr/bin/bash

CONFIGDIR=/var/prologin/wiki/wiki

while read line; do
    user=`echo $line | cut -d ';' -f 1`
    pass=`echo $line | cut -d ';' -f 2`
    echo "creating user $user..."
    moin --config-dir=$CONFIGDIR account create --name $user --password $pass \
        --alias $user --email $user@example.com
done
