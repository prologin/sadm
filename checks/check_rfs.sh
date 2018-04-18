#!/bin/bash
# This script performs various system sanity checks for a live user system

cd $(dirname $0)

source ./checks_common.sh

function main {
  echo_status "systemd units"
  for service in workernode.service \
    presenced.service; do
    test_service_is_enabled_active $service
  done
}

# Run all the checks
main
