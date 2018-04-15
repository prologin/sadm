#!/bin/bash

# Configuration variables
CONTAINER_NAME=pas-r11p11
CONTAINER_HOSTNAME=$CONTAINER_NAME
CONTAINER_MAIN_IP=192.168.0.1
MDB_MACHINE_TYPE=user

GW_CONTAINER_NAME=mygw
RHFS_CONTAINER_NAME=myrhfs0

source ./container_setup_common.sh

container_script_header

function stage_setup_rootfs {
  echo_status 'Fake NFS-root using mount -o bind'

  mkdir -p $CONTAINER_ROOT
  if ! findmnt $CONTAINER_ROOT; then
    mount -o bind,ro /var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot \
       $CONTAINER_ROOT
  fi
}

function stage_setup_network {
  echo_status 'Fake PXE network configuration'

  container_run /usr/bin/ip address replace $CONTAINER_MAIN_IP/23 dev host0
  container_run /usr/bin/ip route replace default via 192.168.1.254
}

# Container script

run container_stop
run stage_setup_rootfs
run container_start

run stage_add_to_mdb

run stage_setup_network
run test_network
