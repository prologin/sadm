#!/bin/bash

source ./common.sh

this_script_must_be_run_as_root

# Configuration variables
CONTAINER_NAME=myweb

CONTAINER_HOSTNAME=web
CONTAINER_MAIN_IP=192.168.1.100
CONTAINER_ALIASES=db,concours,wiki,bugs,redmine,docs,home,paste,map,masternode

GW_CONTAINER_NAME=mygw

source ./container_setup_common.sh

container_script_header

# Setup stages
function stage_setup_network {
  echo_status 'Stage setup network'

  echo '[-] Install SADM network setup'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py systemd_networkd_web nic_configuration
  # Skipped as the container's virtual interface does not support the tweaks we apply
  skip container_run /usr/bin/systemctl enable --now nic-configuration@host0

  echo '[-] Restart systemd-networkd'
  container_run /usr/bin/systemctl restart systemd-networkd

  container_snapshot $FUNCNAME
}

function test_network {
  echo '[>] Test network... '

  echo -n '[>] Check internet access '
  test_url https://gstatic.com/generate_204

  echo -n '[>] Check web.prolo IPs '
  if ! machinectl status $CONTAINER_NAME | grep -q "Address: $CONTAINER_MAIN_IP"; then
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi
}

function stage_setup_udbsync_rootssh {
  echo_status "Setup udbsync_rootssh"

  container_run /var/prologin/venv/bin/python /root/sadm/install.py udbsync_rootssh
  container_run /usr/bin/systemctl enable --now udbsync_rootssh

  container_snapshot $FUNCNAME
}

function stage_setup_udbsync_rootssh {
  echo '[>] Test udbsync_rootssh... '

  #TODO
}

function stage_setup_concours {
  echo_status "Setup udbsync_rootssh"

  container_run /var/prologin/venv/bin/python /root/sadm/install.py concours
  container_run /usr/bin/systemctl enable --now concours
  container_run /usr/bin/systemctl enable --now udbsync_django@concours

  sed 's/# include services_contest/include services_contest/' -i $CONTAINER_ROOT/etc/nginx/nginx.conf

  container_run /usr/bin/systemctl reload nginx

  container_snapshot $FUNCNAME
}

function test_concours {
  echo "[>] Test concours..."

  test_service_is_enabled_active concours
  test_service_is_enabled_active udbsync_django@concours

  test_url http://concours/
}

function stage_setup_masternode {
  echo_status "Setup masternode"

  container_run /var/prologin/venv/bin/python /root/sadm/install.py masternode
  container_run /usr/bin/systemctl enable --now masternode

  container_snapshot $FUNCNAME
}

function test_masternode {
  echo "[>] Test masternode..."

  test_service_is_enabled_active masternode
}

# "container" script
if ! machinectl >/dev/null status $GW_CONTAINER_NAME; then
  echo >&2 "Please start the GW container"
  # TODO: using a VM for GW is also doable, should allow it
  exit 1
fi

run container_stop
run stage_setup_host
run stage_boostrap_arch_linux
run container_start

run stage_add_to_mdb
run stage_allow_root_ssh

run stage_copy_sadm

run stage_setup_sadm
run test_sadm

run stage_setup_libprologin
run test_libprologin

run stage_setup_network
run test_network

run stage_setup_nginx
run test_nginx

run stage_setup_postgresql
run test_postgresql

run stage_setup_concours
run test_concours

run stage_setup_masternode
run test_masternode
