#!/bin/bash

# Configuration variables
CONTAINER_HOSTNAME=pas-r11p11
CONTAINER_NAME=${CONTAINER_HOSTNAME}.prolo
CONTAINER_MAIN_IP=192.168.0.11
MDB_MACHINE_TYPE=user

GW_CONTAINER_NAME=mygw
RHFS_CONTAINER_NAME=myrhfs0

TEST_USER=aproviste

source ./container_setup_common.sh

container_script_header

function stage_setup_rootfs {
  echo_status 'Fake NFS-root using mount -o bind'

  echo '[-] Configure tmpfs that should be configured by initrd hook'
  cat >/var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_staging/etc/fstab <<EOF
# Userland implementation of rfs/initcpio/hooks/prologin
tmpfs /home		tmpfs defaults 0 0
tmpfs /var/log		tmpfs defaults 0 0
tmpfs /var/tmp		tmpfs defaults 0 0
tmpfs /var/spool/mail	tmpfs defaults 0 0
tmpfs /var/lib/isolate	tmpfs defaults 0 0
tmpfs /var/lib/sddm	tmpfs defaults 0 0
EOF

  mkdir -p $CONTAINER_ROOT
  if ! findmnt $CONTAINER_ROOT; then
    mount -o bind,ro /var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_staging \
       $CONTAINER_ROOT
  fi
}

function stage_container_setup {
  echo_status 'Allow /dev/nbd0 to be created in the container'

  echo '[-] Configure container for nbd usage'
  mkdir -p /etc/systemd/system/systemd-nspawn@$CONTAINER_NAME.service.d
  cat >/etc/systemd/system/systemd-nspawn@$CONTAINER_NAME.service.d/override.conf <<EOF
[Service]
DeviceAllow=/dev/nbd0 rwm
EOF

  echo_status 'Fake ndb device'
  cat >/var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_staging/etc/systemd/system/mknod-dev-nbd0.service <<EOF
[Service]
Type=oneshot
ExecStart=/usr/bin/mknod /dev/nbd0 b 43 0

[Install]
WantedBy=default.target
EOF
  systemctl enable mknod-dev-nbd0.service --root /var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_staging/

  echo_status 'Fake PXE network configuration'

  # Create custom configuration
  cat >/var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_staging/etc/systemd/network/10-$CONTAINER_HOSTNAME.network <<EOF
[Match]
Host=$CONTAINER_HOSTNAME.prolo
Name=host0

[Network]
Address=$CONTAINER_MAIN_IP/23
Gateway=192.168.1.254
EOF

  systemctl enable systemd-networkd --root /var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_staging/
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
run container_stop
run container_start

run test_local_network

run stage_user_login
run test_user_login

# User should have access to internet, until the 'user' group is removed from
# firewall whitelist.
run test_internet

echo_status "$CONTAINER_HOSTNAME setup: success!"
