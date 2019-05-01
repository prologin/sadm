#!/bin/bash

source ../common.sh
source ./container_setup_config.sh

this_script_must_be_run_as_root

function container_setup_host {
  echo_status "Configure host for SADM containers"

  echo "[-] Override systemd-nspawn configuration with --network-zone=$NETWORK_ZONE"
  cat >/etc/systemd/system/systemd-nspawn@.service <<EOF
.include /usr/lib/systemd/system/systemd-nspawn@.service

[Service]
ExecStart=
ExecStart=/usr/bin/systemd-nspawn --quiet --keep-unit --boot --link-journal=try-guest --network-zone=$NETWORK_ZONE --settings=override --machine=%i
EOF

  echo "[-] Disable DHCP server for our network zone"
  cat >/etc/systemd/network/80-container-vz-prolo.network <<EOF
[Match]
Name=vz-$NETWORK_ZONE
Driver=bridge

[Network]
# Default to using a /24 prefix, giving up to 253 addresses per virtual network.
Address=10.0.0.1/24
LinkLocalAddressing=yes
IPForward=yes
IPMasquerade=yes
LLDP=yes
EmitLLDP=customer-bridge
EOF

  echo "[-] Restart systemd-networkd"
  systemctl restart systemd-networkd

  echo "[-] Load the nbd kernel module"
  modprobe nbd
}

container_setup_host
