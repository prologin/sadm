#!/bin/bash

# Configuration variables
CONTAINER_HOSTNAME=gw
GW_CONTAINER_NAME=gw
CONTAINER_NAME=mygw

source ./container_setup_common.sh

container_script_header

# Setup stages
function stage_container_gw_network {
  echo_status 'Stage setup basic container network'

  echo "[-] Write static ip container network systemd-networkd configuration"
  cat >$CONTAINER_ROOT/etc/systemd/network/40-gw-container-static.network <<EOF
[Match]
Name=host0

[Network]
Gateway=10.0.0.1
Address=10.0.0.254/24
EOF

  container_run_simple /usr/bin/systemctl restart systemd-networkd

  container_snapshot $FUNCNAME
}

function test_container_gw_network {
  echo '[>] Test gw container network... '

  container_run_simple /usr/bin/ping -c 1 8.8.8.8
}

function stage_setup_network {
  echo_status 'Stage setup network'

  echo '[-] Install SADM network setup'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py systemd_networkd_gw nic_configuration conntrack

  # Skipped as the container's virtual interface does not support the tweaks we apply
  skip container_run /usr/bin/systemctl enable --now nic-configuration@host0

  echo '[-] Enable conntrack'
  container_run /usr/bin/systemctl enable --now conntrack

  echo '[-] Add static ip for container setup'
  cat >> $CONTAINER_ROOT/etc/systemd/network/10-gw.network <<EOF
# Extra static ip and route to communicate with the outside world from within the container
Gateway=10.0.0.1
Address=10.0.0.254/24
EOF

  echo '[-] Restart systemd-networkd'
  container_run /usr/bin/systemctl restart systemd-networkd

  container_snapshot $FUNCNAME
}

function test_network {
  echo '[>] Test network... '

  test_service_is_enabled_active conntrack

  echo -n '[>] Check internet access '
  test_url https://gstatic.com/generate_204

  echo -n '[>] Check gw.prolo IPs '
  if ! machinectl status $CONTAINER_NAME | grep -q '192.168.1.254'; then
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi
}

function stage_setup_gw {
  echo_status 'Run gw setup script'

  container_run /root/sadm/install_scripts/setup_gw.sh

  container_snapshot $FUNCNAME
}

function test_gw {
  echo '[>] Test gw install... '

  #TODO
}

function stage_setup_mdb {
  echo_status 'Install mdb'
  echo '127.0.0.1 mdb' >> $CONTAINER_ROOT/etc/hosts
  container_run /var/prologin/venv/bin/python install.py mdb

  echo '[-] Enable mdb'
  container_run /usr/bin/systemctl enable --now mdb

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx

  # Wait for mdb to start
  sleep 3

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
  echo_status 'Install mdbsync'
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
  echo_status 'Install mdbdns'
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

  echo '[-] Restart services to refresh the libc resolver'
  container_run /usr/bin/systemctl restart mdb

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
  echo_status 'Install mdbdhcp'
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
  echo_status 'Install netboot'
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
  echo_status 'Install tftpd'

  echo '[-] Enable and start the tftpd socket'
  container_run /usr/bin/systemctl enable --now tftpd.socket

  container_snapshot $FUNCNAME
}

function test_tftpd {
  echo '[>] Test tftpd... '

  test_service_is_enabled_active tftpd.socket

  echo '[>] tftpd directory exists'
  test_file_present /srv/tftp

  # TODO test tftp
}

function stage_ipxe {
  echo_status 'Install ipxe'

  # Nothing to do here, the package is already installed

  container_snapshot $FUNCNAME
}

function test_ipxe {
  echo '[>] Test ipxe... '

  echo '[>] ipxe image file exists'
  test_file_present /srv/tftp/prologin.kpxe
}

function stage_udb {
  echo_status 'Install udb'

  echo '[-] Configure udb'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py udb

  echo '[-] Enable and start the udb service'
  container_run /usr/bin/systemctl enable --now udb

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx

  container_snapshot $FUNCNAME
}

function test_udb {
  echo '[>] Test udb... '

  test_service_is_enabled_active udb

  echo '[-] Generate password sheet data for users'
  container_run_verbose /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    pwdsheetdata --type=user

  echo '[-] Generate password sheet data for orgas'
  container_run_verbose /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    pwdsheetdata --type=orga

  echo '[-] Generate password sheet data for roots'
  container_run_verbose /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    pwdsheetdata --type=root
}

function stage_add_users_to_udb {
  echo_status "Add users to udb"

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
root_gw
nathalie
krisboul
marwan
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

function test_users_in_udb {
  echo '[>] Test users in udb'

  #TODO
}

function stage_create_root_ssh_key {
  echo_status 'Create root@gw.prolo ssh credentials'

  # quiet, empty passphrase
  container_run_simple /usr/bin/ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -N ''

  container_snapshot $FUNCNAME
}

function test_root_ssh_key {
  echo '[>] Test root@gw.prolo ssh files... '

  test_file_present /root/.ssh/id_rsa
  test_file_present /root/.ssh/id_rsa.pub
}

function stage_add_ssh_key_to_udb {
  echo_status 'Add root@gw.prolo ssh fingerprint key to udb'

  container_run /var/prologin/venv/bin/python /var/prologin/udb/manage.py \
    usermod root_gw --ssh-pubkey-file /root/.ssh/id_rsa.pub

  container_snapshot $FUNCNAME
}

function test_ssh_key_udb {
  echo '[>] Test root@gw.prolo udb ssh fingerprint... '

  #TODO
}

function stage_udbsync {
  echo_status 'Install udbsync'

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
  echo_status 'Install udbsync clients'

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
  echo_status 'Install presencesync'

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

function stage_sso {
  echo_status 'Install sso'

  #TODO edit nginx.conf and enable SSO

  container_snapshot $FUNCNAME
}

function test_sso {
  echo '[>] Test sso... '

}

function stage_firewall {
  echo_status 'Install firewall'

  echo '[-] Configure firewall'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py firewall

  echo '[-] Enable and start the firewall service'
  container_run /usr/bin/systemctl enable --now firewall

  container_snapshot $FUNCNAME
}

function test_firewall {
  echo '[>] Test firewall... '

  test_service_is_enabled_active firewall
}

function stage_setup_presencesync_firewall {
  echo_status 'Install presencesync firewall'

  echo '[-] Configure firewall with presencesync'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py presencesync_firewall

  echo '[-] Enable and start the firewall with presencesync service'
  container_run /usr/bin/systemctl enable --now presencesync_firewall

  container_snapshot $FUNCNAME
}

function test_presencesync_firewall {
  echo '[>] Test presencesync firewall... '

  test_service_is_enabled_active presencesync_firewall

  #TODO
}

function stage_hfsdb {
  echo_status 'Install hfsdb'

  echo '[-] Configure hfsdb'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py hfsdb

  container_snapshot $FUNCNAME
}

function test_hfsdb {
  echo '[>] Test hfsdb... '

  #TODO
}


# "container" script
run container_stop
run stage_setup_container
run stage_boostrap_arch_linux
run container_start

run stage_container_gw_network
run test_container_gw_network

run stage_copy_sadm

run stage_setup_sadm
run test_sadm

run stage_setup_gw

run stage_setup_libprologin
run test_libprologin

run stage_setup_network
run test_network

run stage_setup_gw
run test_gw

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

run stage_add_users_to_udb
run test_users_in_udb

run stage_create_root_ssh_key
run test_root_ssh_key

run stage_add_ssh_key_to_udb
run test_ssh_key_udb

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

run stage_setup_presencesync_firewall
run test_presencesync_firewall

run stage_hfsdb
run test_hfsdb

container_run_verbose /root/sadm/checks/check_gw.sh

# Display passwords
run test_udb
