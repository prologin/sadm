#!/bin/bash

# Configuration variables
RHFS_ID=0

CONTAINER_NAME=myrhfs$RHFS_ID
CONTAINER_HOSTNAME=rhfs$RHFS_ID
CONTAINER_MAIN_IP=192.168.1.$((RHFS_ID + 1))
MDB_ALIASES=rhfs$RHFS_ID,hfs$RHFS_ID,rfs$RHFS_ID

GW_CONTAINER_NAME=mygw

source ./container_setup_common.sh

container_script_header

# Setup stages

function stage_setup_network {
  echo_status 'Stage setup network'

  echo '[-] Install SADM network setup'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py systemd_networkd_rhfs nic_configuration
  # Skipped as the container's virtual interface does not support the tweaks we apply
  skip container_run /usr/bin/systemctl enable --now nic-configuration@host0

  echo '[-] Restart systemd-networkd'
  container_run /usr/bin/systemctl restart systemd-networkd

  container_snapshot $FUNCNAME
}

function stage_setup_rfs {
  echo_status "Run RFS setup script"

  container_run /root/sadm/install_scripts/setup_rfs.sh

  container_snapshot $FUNCNAME
}

function test_setup_rfs {
  echo '[>] Test rfs... '

  # TODO
}

function stage_setup_rfs_nfs_archlinux {
  echo_status "Install exported Arch Linux"

  echo "[-] Running rfs_nfs_archlinux"
  container_run /var/prologin/venv/bin/python /root/sadm/install.py rfs_nfs_archlinux

  container_snapshot $FUNCNAME
}

function test_rfs_nfs_archlinux {
  echo '[>] Test rfs exported install... '
}

function stage_setup_rfs_nfs_sadm {
  echo_status "Setup exported Arch Linux for SADM"

  echo "[-] Running rfs_nfs_archlinux"
  container_run /var/prologin/venv/bin/python /root/sadm/install.py rfs_nfs_sadm

  echo "[-] Copy kernel and initrd to gw"
  cp -v $CONTAINER_ROOT/export/nfsroot/boot/vmlinuz-linux $CONTAINER_ROOT_GW/srv/tftp/kernel
  cp -v $CONTAINER_ROOT/export/nfsroot/boot/initramfs-linux-fallback.img $CONTAINER_ROOT_GW/srv/tftp/initrd

  container_snapshot $FUNCNAME
}

function test_rfs_nfs_sadm {
  echo '[>] Test rfs exported sadm... '
}

function stage_install_rfs_nfs_packages_base {
  echo_status "Setup base rfs nfs packages"

  echo "[-] Install base packages"
  container_run /var/prologin/venv/bin/python /root/sadm/install.py rfs_nfs_packages_base

  container_snapshot $FUNCNAME
}

function test_rfs_nfs_packages_base {
  echo '[>] Test base rfs packages... '
  # TODO
}

function stage_install_rfs_nfs_packages_extra {
  echo_status "Setup extra rfs nfs packages"

  echo "[-] Install extra packages"
  container_run /var/prologin/venv/bin/python /root/sadm/install.py rfs_nfs_packages_extra

  container_snapshot $FUNCNAME
}

function test_rfs_nfs_packages_extra {
  echo '[>] Test extra rfs packages... '
  # TODO
}

function stage_install_rfs {
  echo_status "Setup rfs"

  echo "[-] Install rfs"
  container_run /var/prologin/venv/bin/python /root/sadm/install.py rfs

  for svc in {udbsync_passwd{,_nfsroot},udbsync_rootssh,rpcbind,nfs-server}.service rootssh.path; do
    echo "[-] Enable $svc"
    container_run /usr/bin/systemctl enable --now "$svc"
  done

  container_snapshot $FUNCNAME
}

function test_install_rfs {
  echo '[>] Test rfs install... '

  # Give time to services to start
  sleep 10

  for svc in udbsync_passwd{,_nfsroot},udbsync_rootssh,rpcbind,nfs-server}.service rootssh.path; do
      test_service_is_enabled_active "$svc"
  done

  echo -n '[>] NFS export... '
  exports=$(container_run_verbose /usr/bin/exportfs -s)
  if echo "$exports" | grep -q /export/nfsroot; then
    echo_ok "OK"
  else
    echo_ko "KO"
  fi
}

function stage_install_hfs {
  echo_status "Install hfs"

  container_run /var/prologin/venv/bin/python /root/sadm/install.py hfs

  echo "[-] Enable and start hfs@$RHFS_ID"
  container_run /usr/bin/systemctl enable --now hfs@$RHFS_ID

  # Wait for HFS to start
  sleep 10

  container_snapshot $FUNCNAME
}

function test_install_hfs {
  echo '[>] Test hfs install... '

  test_service_is_enabled_active hfs@$RHFS_ID

  test_file_present /export/skeleton

  echo '[>] Test create home dir... '
  container_run /usr/bin/curl hfs$RHFS_ID:20100/get_hfs --data "'data={\"user\":\"jmarchand\",\"hfs\":$RHFS_ID,\"utype\":\"user\"}'"
}


# "container" script
if ! machinectl >/dev/null status $GW_CONTAINER_NAME; then
  echo >&2 "Please start the GW container"
  # TODO: using a VM for GW is also doable, should allow it
  exit 1
fi

run container_stop
run stage_setup_container
run stage_boostrap_arch_linux
run container_start

run stage_copy_sadm

run stage_add_to_mdb
run stage_allow_root_ssh

run stage_setup_sadm
run test_sadm

run stage_setup_libprologin
run test_libprologin

run stage_setup_network
run test_network

# RFS

run stage_setup_rfs
run test_setup_rfs

run stage_setup_rfs_nfs_archlinux
run test_rfs_nfs_archlinux

run stage_setup_rfs_nfs_sadm
run test_rfs_nfs_sadm

run stage_install_rfs
run test_install_rfs

run stage_install_rfs_nfs_packages_base
run test_rfs_nfs_packages_base

# Skipping as not necessary for basic tests
skip stage_install_rfs_nfs_packages_extra
skip test_rfs_nfs_packages_extra

# HFS

run stage_install_hfs
run test_install_hfs

container_run_verbose /root/sadm/checks/check_rhfs.sh
