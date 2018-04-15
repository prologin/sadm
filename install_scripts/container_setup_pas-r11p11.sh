#!/bin/bash

# Configuration variables
CONTAINER_NAME=pas-r11p11
CONTAINER_HOSTNAME=$CONTAINER_NAME
CONTAINER_MAIN_IP=192.168.0.1
MDB_MACHINE_TYPE=user

GW_CONTAINER_NAME=mygw
RHFS_CONTAINER_NAME=myrhfs0

TEST_USER=aproviste

source ./container_setup_common.sh

container_script_header

function stage_setup_rootfs {
  echo_status 'Fake NFS-root using mount -o bind'

  mkdir -p $CONTAINER_ROOT
  if ! findmnt $CONTAINER_ROOT; then
    mount -o bind,ro /var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot \
       $CONTAINER_ROOT
  fi

  echo '[-] Configure tmpfs'

  cat >/var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_mnt/etc/fstab <<EOF
# Userland implementation of rfs/initcpio/hooks/prologin
tmpfs /home		tmpfs defaults 0 0
tmpfs /var/log		tmpfs defaults 0 0
tmpfs /var/tmp		tmpfs defaults 0 0
tmpfs /var/spool/mail	tmpfs defaults 0 0
tmpfs /var/lib/isolate	tmpfs defaults 0 0
tmpfs /var/lib/sddm	tmpfs defaults 0 0
EOF
}

function stage_container_setup {
  echo_status 'Allow /dev/nbd0 to be created in the container'

  cat >/etc/systemd/system/systemd-nspawn@$CONTAINER_NAME.service.d/override.conf <<EOF
[Service]
DeviceAllow=/dev/nbd0 rwm
EOF

}

function stage_setup_network {
  echo_status 'Fake PXE network configuration'

  container_run /usr/bin/ip address replace $CONTAINER_MAIN_IP/23 dev host0
  container_run /usr/bin/ip link set dev host0 up
  container_run /usr/bin/ip route replace default via 192.168.1.254
}

function stage_setup_nbd {
  echo_status 'Create ndb device'

  container_run /usr/bin/mknod /dev/nbd0 b 43 0
}

function stage_user_login {
  echo_status 'Login user'

  container_run /usr/bin/pamtester login $TEST_USER open_session
}

function test_user_login {
  echo '[>] Test rfs install... '

  container_run /usr/bin/findmnt /home/$TEST_USER
}

# Container script

run container_stop
run stage_setup_rootfs
run stage_container_setup
run container_start

run stage_add_to_mdb

run stage_setup_network
run test_network

run stage_setup_nbd

run stage_user_login
run test_user_login
