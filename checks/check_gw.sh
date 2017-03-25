#!/bin/bash
# This script performs various system sanity checks for gw.prolo

# Logging functions
function echo_status {
 # blue foreground, then default foreground
  echo -e "\e[34m[+] $*\e[39m"
}

function echo_ko {
  # red foreground, then default foreground
  echo -e "\e[31m$*\e[39m"
}

function echo_ok {
  # green foreground, then default foreground
  echo -e "\e[32m$*\e[39m"
}

function test_service_is_enabled_active {
  service=$1
  service_status=$(systemctl is-active $service)

  echo -n "$service is $service_status "
  if [[ $service_status == active ]]; then
    echo_ok "OK"
  else
    echo_ko "FAIL: should be active"
  fi

  service_status=$(systemctl is-enabled $service)
  echo -n "$service is $service_status "
  if [[ $service_status == enabled ]]; then
    echo_ok "OK"
  else
    echo_ko "FAIL: should be enabled"
  fi
}

function test_file_present {
  filename=$1
  echo -n "$filename is "
  if [[ -e $filename ]]; then
    echo_ok "present"
  else
    echo_ko "absent"
  fi
}

function main {
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
  test_file_present /srv/tftp/prologin.kpxe
}

# Run all the checks
main
