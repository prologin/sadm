#!/bin/sh

set -e

for serv in rfs{2,4,6}; do
    echo "######## SYNCING $serv ########"
    rsync -axPHAX /export/nfsroot/ "$serv":/export/nfsroot
    rsync -axPHAX /export/skeleton/ "$serv":/export/skeleton
done
