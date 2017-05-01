#!/bin/sh

set -e

echo "######## SYNCING staging ########"
rsync --delete -axPHAX /export/nfsroot_staging/ /export/nfsroot
