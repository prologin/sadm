#!/bin/bash
# This script performs various system sanity checks for gw.prolo

cd $(dirname $0)

source ./checks_common.sh

function main {
  echo_status "hostname"
  check_hostname gw

  echo_status "network"
  check_ip 192.168.1.254
  check_ip 192.168.250.254

  echo_status "systemd units"
  for service in systemd-networkd.service \
    postgresql.service \
    mdb.service \
    nginx.service \
    mdbsync.service \
    mdbdns.service \
    named.service \
    mdbdhcp.service \
    dhcpd4.service \
    netboot.service \
    tftpd.socket \
    udb.service \
    udbsync.service \
    udbsync_django@mdb.service \
    udbsync_django@udb.service \
    udbsync_rootssh.service \
    presencesync.service \
    presencesync_cacheserver.service \
    firewall.service \
    presencesync_firewall.service; do
    test_service_is_enabled_active $service
  done

  echo_status "files"
  test_file_present /srv/tftp/arch.kpxe
  test_file_present /srv/tftp/prologin.kpxe
  test_file_present /srv/tftp/initrd
  test_file_present /srv/tftp/vmlinuz
}

# Run all the checks
main
