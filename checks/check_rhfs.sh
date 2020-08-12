#!/bin/bash
# This script performs various system sanity checks for rhfsAB.prolo

cd $(dirname $0)

source ./checks_common.sh

function main {
  echo_status "systemd units"
  for svc in {udbsync_passwd{,_nfsroot},udbsync_rootssh,rpcbind,nfs-server}.service rootssh.path; do
    test_service_is_enabled_active "$svc"
  done


  echo_status "network"
  not_in_alien_subnet

  echo_status "files"
  test_file_present /export/nfsroot/boot/initramfs-linux-fallback.img
  test_file_present /export/nfsroot/boot/vmlinuz-linux
}

main
