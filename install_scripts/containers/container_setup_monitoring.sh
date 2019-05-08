#!/bin/bash

# Configuration variables
CONTAINER_NAME=mymon

CONTAINER_HOSTNAME=mon
CONTAINER_MAIN_IP=192.168.1.101

GW_CONTAINER_NAME=mygw

source ./container_setup_common.sh

container_script_header

# Setup stages
function stage_setup_monitoring {
  echo_status 'Run monitoring setup script'

  container_run /root/sadm/install_scripts/setup_monitoring.sh

  container_snapshot $FUNCNAME
}

function stage_setup_prometheus {
  echo_status 'Setup prometheus'

  container_run /opt/prologin/venv/bin/python /root/sadm/install.py prometheus
  container_run /usr/bin/mv /etc/prometheus/prometheus.yml{.new,}

  echo '[-] Enable and start prometheus'
  container_run /usr/bin/systemctl enable --now prometheus

  container_snapshot $FUNCNAME
}

function test_prometheus {
  echo '[>] Test prometheus... '

  # Fetch prometheus' own metrics
  test_url http://localhost:9090/metrics
}

function stage_setup_grafana {
  echo_status 'Setup grafana'

  container_run /opt/prologin/venv/bin/python /root/sadm/install.py grafana

  echo '[-] Enable and start grafana'
  container_run /usr/bin/systemctl enable --now grafana

  container_snapshot $FUNCNAME
}

function test_grafana {
  echo '[>] Test grafana... '

  # TODO
}

# "container" script
run container_stop
run stage_setup_container
run stage_bootstrap_arch_linux
run container_start

run stage_add_to_mdb
run container_stop
run container_start

run stage_allow_root_ssh

run stage_copy_sadm

run stage_setup_sadm
run test_sadm

run stage_setup_monitoring

run stage_setup_libprologin
run test_libprologin

run stage_setup_prometheus
run test_prometheus

run stage_setup_grafana
run test_grafana

echo_status "$CONTAINER_HOSTNAME setup: success!"
