#!/bin/bash

# Configuration variables
CONTAINER_HOSTNAME=pas-r11p11
CONTAINER_NAME=${CONTAINER_HOSTNAME}.prolo
CONTAINER_MAIN_IP=192.168.0.11
MDB_MACHINE_TYPE=user

GW_CONTAINER_NAME=mygw
RHFS_ID=0
RHFS_CONTAINER_NAME=myrhfs$RHFS_ID

TEST_USER=aproviste

source ./container_setup_common.sh

container_script_header

function stage_container_setup {
  echo_status 'Allow /dev/nbd0 to be created in the container'

  echo '[-] Create specific .nspawn file'
  cat >/etc/systemd/nspawn/$CONTAINER_NAME.nspawn <<EOF
[Network]
Zone=prolo

[Files]
PrivateUsersChown=false
ReadOnly=true
Bind=/dev/nbd0

TemporaryFileSystem=/home
TemporaryFileSystem=/var/log
TemporaryFileSystem=/var/tmp
TemporaryFileSystem=/var/spool/mail
TemporaryFileSystem=/var/lib/isolate
TemporaryFileSystem=/var/lib/lightdm
TemporaryFileSystem=/var/lib/lightdm-data
EOF

  echo '[-] Configure container for nbd usage'
  mkdir -p /etc/systemd/system/systemd-nspawn@$CONTAINER_NAME.service.d
  cat >/etc/systemd/system/systemd-nspawn@$CONTAINER_NAME.service.d/override.conf <<EOF
[Service]
DeviceAllow=/dev/nbd0 rwm
EOF

  echo_status 'Fake PXE network configuration'

  # Create static network configuration. Normally IP should be configured
  # through DHCP as part of the boot process, which is not done here.
  cat >/var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_staging/etc/systemd/network/10-$CONTAINER_HOSTNAME.network <<EOF
[Match]
Host=$CONTAINER_HOSTNAME.prolo
Name=host0

[Network]
Address=$CONTAINER_MAIN_IP/23
Gateway=192.168.1.254
EOF

  systemctl enable systemd-networkd --root /var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_staging/

  echo '[-] Commit staging nfs in rfs'
  (
    CONTAINER_NAME=$RHFS_CONTAINER_NAME
    CONTAINER_ROOT=/var/lib/machines/$CONTAINER_NAME
    container_run /root/sadm/rfs/commit_staging.sh rfs$RHFS_ID
  )
}

function stage_setup_rootfs {
  echo_status 'Fake NFS-root using mount -o bind,ro'

  mkdir -p $CONTAINER_ROOT
  umount -q $CONTAINER_ROOT || true
  mount -o bind,ro /var/lib/machines/$RHFS_CONTAINER_NAME/export/nfsroot_ro \
     $CONTAINER_ROOT
}

function stage_user_login {
  echo_status 'Login user'

  container_run /usr/bin/pamtester login $TEST_USER open_session
}

function test_user_login {
  echo '[>] Test user login... '

  container_run /usr/bin/findmnt /home/$TEST_USER
}

function stage_user_logout {
  echo_status 'Logout user'

  container_run /usr/bin/pamtester login $TEST_USER close_session
}

function test_user_logout {
  echo '[>] Test user logout... '

  # TODO
}

# Container script

run container_stop
run stage_container_setup
run stage_setup_rootfs
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

run stage_user_logout
run test_user_logout

echo_status "$CONTAINER_HOSTNAME setup: success!"
