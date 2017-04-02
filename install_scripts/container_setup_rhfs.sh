#!/bin/bash

source ./common.sh

this_script_must_be_run_as_root

cat <<EOF
[+] Welcome to the container setup of SADM!
EOF

# Configuration variables
USE_BTRFS=true

CONTAINER_NAME=mygw
NETWORK_ZONE=prolo

# Secrets
ROOT_PASSWORD=101010
SADM_MASTER_SECRET=lesgerbillescesttropfantastique

# Other variables
CONTAINER_ROOT=/var/lib/machines/$CONTAINER_NAME
SADM_ROOT_DIR=$(dirname $PWD)

# Container and snapshots functions
function container_snapshot {
  if $USE_BTRFS; then
    snapshot_name=$1
    snapshot_root=${CONTAINER_ROOT}_$snapshot_name

    echo "[+] Snapshot to $snapshot_root"

    if [ -d $snapshot_root ]; then
      # remove existing snapshot
      btrfs subvolume delete $snapshot_root
    fi
    # make the read-only snapshot
    btrfs subvolume snapshot -r $CONTAINER_ROOT $snapshot_root
  fi
}

function container_stop {
  echo "[+] Stop container"
  if machinectl >&- status $CONTAINER_NAME; then
    machinectl stop $CONTAINER_NAME && sleep 1
    machinectl kill $CONTAINER_NAME && sleep 1
    machinectl terminate $CONTAINER_NAME && sleep 1
  fi
  # Some race condition keep the service active even though not registered in machined
  if systemctl >&- is-active systemd-nspawn@$CONTAINER_NAME.service; then
    systemctl stop systemd-nspawn@$CONTAINER_NAME.service
  fi
}

function container_start {
  echo "[+] Spawn container with 5 seconds delay to have systemd start"
  machinectl start $CONTAINER_NAME && sleep 5

  echo '[-] Containers on this system:'
  machinectl list

  echo "[-] You can now login to $CONTAINER_NAME as root:$ROOT_PASSWORD using:"
  echo "  # machinectl login $CONTAINER_NAME"
}

function container_run {
  # PATH is configured for the python virtualenv
  # Send dummy input else systemd-run will wait for user input
  systemd-run -M $CONTAINER_NAME --wait \
    --property WorkingDirectory=/root/sadm \
    --setenv=PATH=/var/prologin/venv/bin:/usr/bin \
    "$@"
}

function container_run_quiet {
  systemd-run --quiet -M $CONTAINER_NAME --pty --wait \
    --property WorkingDirectory=/root/sadm \
    --setenv=PATH=/var/prologin/venv/bin:/usr/bin \
    "$@"
}

# Script directives
function skip {
  # do nothing
  echo "[+] Skip: $*"
}

function run {
  $*
}

function restore {
  snapshot_name=$1
  snapshot_root=${CONTAINER_ROOT}_$snapshot_name

  echo "[+] Snapshot restore of $snapshot_root"
  container_stop

  if [ -d $CONTAINER_ROOT ]; then
    btrfs subvolume delete $CONTAINER_ROOT/var/lib/machines || true  # this can fail if we restored a snapshot
    btrfs subvolume delete $CONTAINER_ROOT
  fi
  # restore the snapshot as read+write
  btrfs subvolume snapshot $snapshot_root $CONTAINER_ROOT

  container_start
}

# Test functions
function test_service_is_enabled_active {
  service=$1

  # "enabled" check
  echo -n "[>] $service is "
  service_enabled=$(systemctl -M $CONTAINER_NAME is-enabled $service || true)
  echo -n "$service_enabled "
  if [[ $service_enabled == enabled ]]; then
    echo_ok "PASS"
  else
    echo_ko "FAIL: should be enabled"
    return 1
  fi

  # "active" check
  echo -n "[>] $service is "

  while [[ -z $service_status || $service_status == activating ]]; do
    service_status=$(systemctl -M $CONTAINER_NAME is-active $service || true)
  done

  echo -n "$service_status "

  if [[ $service_status == active ]]; then
    echo_ok "PASS"
  else
    echo_ko "FAIL: should be active"
    return 1
  fi
}

# Setup stages
function stage_setup_host {
  echo "[+] Override systemd-nspawn configuration with --network-zone=$NETWORK_ZONE"
  cat >/etc/systemd/system/systemd-nspawn@$CONTAINER_NAME.service <<EOF
.include /usr/lib/systemd/system/systemd-nspawn@.service

[Service]
ExecStart=
ExecStart=/usr/bin/systemd-nspawn --quiet --keep-unit --boot --link-journal=try-guest --network-zone=$NETWORK_ZONE -U --settings=override --machine=%i
EOF

  echo "[-] Create $CONTAINER_ROOT"
  if $USE_BTRFS; then
    if [ -d $CONTAINER_ROOT ]; then
      btrfs subvolume delete $CONTAINER_ROOT/var/lib/machines || true  # this can fail if we restored a snapshot
      btrfs subvolume delete $CONTAINER_ROOT
    fi
    btrfs subvolume create $CONTAINER_ROOT
  else
    mkdir -p $CONTAINER_ROOT
  fi

  echo $ROOT_PASSWORD > ./plaintext_root_pass

  container_snapshot $FUNCNAME
}

function stage_boostrap_arch_linux {
  ./bootstrap_arch_linux.sh $CONTAINER_ROOT gw ./plaintext_root_pass

  container_snapshot $FUNCNAME
}

function stage_setup_sadm {
  echo "[+] Copy $SADM_ROOT_DIR to the container"
  cp -r $SADM_ROOT_DIR $CONTAINER_ROOT/root/sadm

  echo "[-] Configure DNS resolver"
  # No need to setup systemd-network, it has already been enabled by the setup
  # script and systemd has a default network file for containers.
  cp -v ../etc/resolv.conf.gw $CONTAINER_ROOT/etc/resolv.conf

  echo "[-] Start sadm setup script"
  container_run /root/sadm/install_scripts/setup_sadm.sh

  container_snapshot $FUNCNAME
}

function test_sadm {
  echo '[>] Test SADM... '

  echo '[>] sadm directory exists'
  container_run_quiet /usr/bin/test -d /root/sadm
}

function stage_setup_network {
  echo '[+] Stage setup network'

  container_run /var/prologin/venv/bin/python /root/sadm/install.py systemd_networkd nic_configuration conntrack
  # Skipped as the container's virtual interface does not support the tweaks we apply
  skip container_run /usr/bin/systemctl enable --now nic-configuration@host0
  container_run /usr/bin/systemctl enable --now conntrack
  container_run /usr/bin/systemctl restart systemd-networkd

  container_snapshot $FUNCNAME
}

function test_network {
  echo '[>] Test network... '

  test_service_is_enabled_active conntrack

  echo -n '[>] Check internet access '
  if ! container_run_quiet /usr/bin/curl https://gstatic.com/generate_204; then
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi

  echo -n '[>] Check gw.prolo IPs '
  if ! container_run_quiet /usr/bin/ip address show host0 | grep -q 192.168.1.254; then
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi
}


function stage_setup_libprologin {
  echo '[+] Stage setup libprologin and SADM master secret'

  echo '[-] Install master secret'
  container_run --setenv=PROLOGIN_SADM_MASTER_SECRET="$SADM_MASTER_SECRET" /var/prologin/venv/bin/python install.py sadm_secret
  echo '[-] Install libprologin'
  container_run /var/prologin/venv/bin/python install.py libprologin

  container_snapshot $FUNCNAME
}

function test_libprologin {
  echo '[>] Test libprologin... '

  echo '[>] Import prologin'
  container_run /var/prologin/venv/bin/python -c 'import prologin'
}

function stage_setup_postgresql {
  echo '[+] Stage setup postgresql'

  echo '[-] Configure postgresql'
  container_run /var/prologin/venv/bin/python install.py postgresql

  echo '[-] Enable and start the postgresql service'
  container_run /usr/bin/systemctl enable --now postgresql

  container_snapshot $FUNCNAME
}

function test_postgresql {
  echo '[>] Test postgresql... '

  test_service_is_enabled_active postgresql

  echo -n '[>] Connect to postgresql '
  if ! container_run_quiet /usr/bin/psql -U postgres -c '\l'; then
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi
}

function stage_setup_nginx {
  echo '[+] Stage setup nginx'

  container_run /usr/bin/pacman -S --noconfirm openresty

  container_run /var/prologin/venv/bin/python install.py nginxcfg
  container_run /usr/bin/mv /etc/nginx/nginx.conf{.new,}

  echo '[-] Enable nginx'
  container_run /usr/bin/systemctl enable --now nginx

  container_snapshot $FUNCNAME
}

function test_nginx {
  echo '[>] Test nginx... '

  test_service_is_enabled_active nginx
}

function stage_setup_mdb {
  echo '[+] Install mdb'
  echo '127.0.0.1 mdb' >> $CONTAINER_ROOT/etc/hosts
  container_run /var/prologin/venv/bin/python install.py mdb

  echo '[-] Enable mdb'
  container_run /usr/bin/systemctl enable --now mdb

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx

  container_snapshot $FUNCNAME
}

function test_mdb {
  echo '[>] Test mdb... '

  test_service_is_enabled_active mdb

  echo -n '[>] GET http://mdb/query '
  if ! container_run_quiet >&- /usr/bin/curl --fail http://mdb/query; then
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi
}

function stage_setup_mdbsync {
  echo '[+] Install mdbsync'
  container_run /var/prologin/venv/bin/python install.py mdbsync
  echo '127.0.0.1 mdbsync' >> $CONTAINER_ROOT/etc/hosts

  echo '[-] Enable and start the mdbsync service'
  container_run /usr/bin/systemctl enable --now mdbsync

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx

  container_snapshot $FUNCNAME
}

function test_mdbsync {
  echo '[>] Test mdbsync... '

  test_service_is_enabled_active mdbsync
}

function stage_setup_mdbdns {
  echo '[+] Install mdbdns'
  container_run /var/prologin/venv/bin/python install.py mdbdns

  container_run /usr/bin/mv /etc/named.conf{.new,}
  echo '[-] Enable and start the mdbdns service'
  container_run /usr/bin/systemctl enable --now mdbdns

  container_run /var/prologin/venv/bin/python /var/prologin/mdb/manage.py \
    addmachine --hostname gw --mac 11:22:33:44:55:66 \
      --ip 192.168.1.254 --rfs 0 --hfs 0 --mtype service --room pasteur \
      --aliases mdb,mdbsync,ns,netboot,udb,udbsync,presencesync,ntp

  # Delay for the generated files to be written
  sleep .5

  echo '[-] Enable and start the named (sic) service'
  container_run /usr/bin/systemctl enable --now named

  # Delay for named to get its little brain up and running
  sleep .5

  echo '[-] Reset /etc/hosts'
  sed -i '/# End of file/q' $CONTAINER_ROOT/etc/hosts

  echo '[-] Set gw as its own DNS resolver'
  sed -i 's/#nameserver 127.0.0.1/nameserver 127.0.0.1/' $CONTAINER_ROOT/etc/resolv.conf
  sed -i 's/nameserver 8.8.8.8/#nameserver 8.8.8.8/' $CONTAINER_ROOT/etc/resolv.conf

  container_snapshot $FUNCNAME
}

function test_mdbdns {
  echo '[>] Test mdbdns... '

  ret=$(container_run_quiet /usr/bin/host mdb.prolo 127.0.0.1 | grep 'mdb.prolo has address' | cut -d' ' -f 4 | tr -d '\r\n')
  expected=192.168.1.254
  if [[ $ret != $expected ]]; then
    echo_ko "FAIL, expected $expected, got $ret"
    return 1
  else
    echo_ok PASS
  fi

  test_service_is_enabled_active mdbdns
  test_service_is_enabled_active named
}

function stage_setup_mdbdhcp {
  echo '[+] Install mdbdhcp'
  container_run /var/prologin/venv/bin/python install.py mdbdhcp

  echo '[-] Enable and start the mdbdhcp service'
  container_run /usr/bin/systemctl enable --now mdbdhcp

  echo '[-] Download Arch Linux PXE image served by dhcpd'
  container_run /usr/bin/wget https://www.archlinux.org/static/netboot/ipxe.pxe -O /srv/tftp/arch.kpxe

  echo '[-] Edit dhpcd.conf'
  container_run /usr/bin/mv /etc/dhcpd.conf{.new,}
  container_run /usr/bin/sed -i '/subnet XX.XX.0.0 netmask 255.255.0.0/a \\    subnet 169.254.0.0 netmask 255.255.0.0 { }' /etc/dhcpd.conf
  container_run /usr/bin/sed -i '/subnet XX.XX.0.0 netmask 255.255.0.0/a \\    subnet 10.0.0.0 netmask 255.255.255.0 { }' /etc/dhcpd.conf

  echo '[-] Enable and start the dhcpd4 service'
  container_run /usr/bin/systemctl enable --now dhcpd4

  container_snapshot $FUNCNAME
}

function test_mdbdhcp {
  echo '[>] Test mdbdhcp... '

  test_service_is_enabled_active mdbdhcp
  test_service_is_enabled_active dhcpd4
}

function stage_netboot {
  echo '[+] Install netboot'
  container_run /var/prologin/venv/bin/python install.py netboot

  echo '[-] Enable and start the netboot service'
  container_run /usr/bin/systemctl enable --now netboot

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx

  container_snapshot $FUNCNAME
}

function test_netboot {
  echo '[>] Test netboot... '
  #TODO
}

function stage_tftpd {
  echo '[+] Install tftpd'

  echo '[-] Enable and start the tftpd socket'
  container_run /usr/bin/systemctl enable --now tftpd.socket

  container_snapshot $FUNCNAME
}

function test_tftpd {
  echo '[>] Test tftpd... '

  test_service_is_enabled_active tftpd.socket

  echo '[>] tftpd directory exists'
  container_run_quiet /usr/bin/test -d /srv/tftp

  # TODO test tftp
}

function stage_ipxe {
  echo '[+] Install ipxe'

  container_run /usr/bin/pacman -S --noconfirm ipxe-sadm-git

  container_snapshot $FUNCNAME
}

function test_ipxe {
  echo '[>] Test ipxe... '

  echo '[>] ipxe image file exists'
  container_run_quiet /usr/bin/test -e /srv/tftp/prologin.kpxe
}

function stage_udb {
  echo '[+] Install udb'

  echo '[-] Configure udb'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py udb

  echo '[-] Enable and start the udb service'
  container_run /usr/bin/systemctl enable --now udb

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx

  echo '[-] Create dummy user files'
  cat >$CONTAINER_ROOT/root/finalistes.txt <<EOF
Alain	Proviste
Joseph	Marchand
EOF

  cat >$CONTAINER_ROOT/root/orgas.txt <<EOF
cana_p
login_x
EOF

  cat >$CONTAINER_ROOT/root/roots.txt <<EOF
lu_k
EOF

  echo '[-] Start batch import for users'
  container_run /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    batchimport --file=/root/finalistes.txt

  echo '[-] Start batch import for orgas'
  container_run /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    batchimport --logins --type=orga --pwdlen=10 --file=/root/orgas.txt

  echo '[-] Start batch import for root'
  container_run /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    batchimport --logins --type=root --pwdlen=10 --file=/root/roots.txt

  container_snapshot $FUNCNAME
}

function test_udb {
  echo '[>] Test udb... '

  test_service_is_enabled_active udb

  echo '[-] Generate password sheet data for users'
  container_run /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    pwdsheetdata --type=user

  echo '[-] Generate password sheet data for orgas'
  container_run /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    pwdsheetdata --type=orga

  echo '[-] Generate password sheet data for roots'
  container_run /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    pwdsheetdata --type=root
}

function stage_udbsync {
  echo '[+] Install udbsync'

  echo '[-] Configure udbsync'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py udbsync

  echo '[-] Enable and start the udbsync service'
  container_run /usr/bin/systemctl enable --now udbsync

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx


  container_snapshot $FUNCNAME
}

function test_udbsync {
  echo '[>] Test udbsync... '

  test_service_is_enabled_active udbsync
  # TODO more test
}

function stage_udbsync_clients {
  echo '[+] Install udbsync clients'

  echo '[-] Configure udbsync_django udbsync_rootssh'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py udbsync_django udbsync_rootssh

  echo '[-] Enable and start the udbsync_django@mdb service'
  container_run /usr/bin/systemctl enable --now udbsync_django@mdb

  echo '[-] Enable and start the udbsync_django@udb service'
  container_run /usr/bin/systemctl enable --now udbsync_django@udb

  echo '[-] Enable and start the udbsync_rootssh service'
  container_run /usr/bin/systemctl enable --now udbsync_rootssh

  container_snapshot $FUNCNAME
}

function test_udbsync_clients {
  echo '[>] Test udbsync clients... '

  test_service_is_enabled_active udbsync_django@mdb
  test_service_is_enabled_active udbsync_django@udb
  test_service_is_enabled_active udbsync_rootssh

  # TODO more test
}

function stage_presencesync {
  echo '[+] Install presencesync'

  echo '[-] Configure presencesync'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py presencesync

  echo '[-] Enable and start the presencesync service'
  container_run /usr/bin/systemctl enable --now presencesync

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx

  container_snapshot $FUNCNAME
}

function test_presencesync {
  echo '[>] Test presencesync... '

  test_service_is_enabled_active presencesync

  # TODO more test
}

function stage_presencesync_cacheserver {
  echo '[+] Install presencesync cacheserver'

  echo '[-] Configure presencesync cacheserver'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py presencesync_cacheserver

  echo '[-] Enable and start the presencesync cacheserevr service'
  container_run /usr/bin/systemctl enable --now presencesync_cacheserver

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx

  container_snapshot $FUNCNAME
}

function test_presencesync_cacheserver {
  echo '[>] Test presencesync... '

  test_service_is_enabled_active presencesync_cacheserver

  # TODO more test
}

function stage_sso {
  echo '[+] Install sso'

  #TODO edit nginx.conf and enable SSO

  container_snapshot $FUNCNAME
}

function test_sso {
  echo '[>] Test sso... '

}

function stage_firewall {
  echo '[+] Install firewall'

  echo '[-] Configure firewall'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py firewall

  echo '[-] Enable and start the firewall service'
  container_run /usr/bin/systemctl enable --now firewall

  echo '[-] Configure firewall with presencesync'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py presencesync_firewall

  echo '[-] Enable and start the firewall with presencesync service'
  container_run /usr/bin/systemctl enable --now presencesync_firewall

  container_snapshot $FUNCNAME
}

function test_firewall {
  echo '[>] Test firewall... '

  test_service_is_enabled_active firewall
  test_service_is_enabled_active presencesync_firewall
}

# "container" script
run container_stop
run stage_setup_host
run stage_boostrap_arch_linux
run container_start

run stage_setup_sadm
run test_sadm

run stage_setup_libprologin
run test_libprologin

run stage_setup_network
run test_network

run stage_setup_postgresql
run test_postgresql

run stage_setup_nginx
run test_nginx

run stage_setup_mdb
run test_mdb

run stage_setup_mdbsync
run test_mdbsync

run stage_setup_mdbdns
run test_mdbdns

run stage_setup_mdbdhcp
run test_mdbdhcp

run stage_netboot
run test_netboot

run stage_tftpd
run test_tftpd

run stage_ipxe
run test_ipxe

run stage_udb
run test_udb

run stage_udbsync
run test_udbsync

run stage_udbsync_clients
run test_udbsync_clients

run stage_presencesync
run test_presencesync

run stage_presencesync_cacheserver
run test_presencesync_cacheserver

run stage_sso
run test_sso

run stage_firewall
run test_firewall
