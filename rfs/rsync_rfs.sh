#!/bin/sh

set -e

for serv in rfs{2,4,6}; do
    echo "######## SYNCING $serv ########"
    rsync --delete -axPHAX /export/nfsroot/ "$serv":/export/nfsroot
    rsync --delete -axPHAX /export/skeleton/ "$serv":/export/skeleton
done
