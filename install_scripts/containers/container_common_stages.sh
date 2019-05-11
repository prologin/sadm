source ./container_setup_config.sh

# Common setup stages
function stage_setup_container {
  echo "[-] Create $CONTAINER_ROOT"
  if $USE_BTRFS; then
    if [ -d $CONTAINER_ROOT ]; then
      container_remove_btrfs_root
    fi
    btrfs subvolume snapshot $ARCH_LINUX_BASE_ROOT $CONTAINER_ROOT
  else
    rsync --partial --info=progress2 -ha $ARCH_LINUX_BASE_ROOT/ $CONTAINER_ROOT
  fi

  echo "[-] Create $CONTAINER_NAME.nspawn configuration file"
  mkdir -p /etc/systemd/nspawn
  cat >/etc/systemd/nspawn/$CONTAINER_NAME.nspawn <<EOF
[Network]
Zone=$NETWORK_ZONE

[Files]
# Allows cp-ing from container to container
PrivateUsersChown=false
EOF
}

function stage_bootstrap_arch_linux {
  echo_status "Bootstrap Arch Linux"

  # Set hostname
  echo $CONTAINER_HOSTNAME >$CONTAINER_ROOT/etc/hostname

  # Asking for host key verification breaks non-interactive scripts, disable it
  mkdir -p $CONTAINER_ROOT/root/.ssh
  cat >>$CONTAINER_ROOT/root/.ssh/config <<EOF
Host *
    StrictHostKeyChecking no
EOF

  container_snapshot $FUNCNAME
}

function stage_copy_sadm {
  echo_status "Copy $SADM_ROOT_DIR to the container"

  rm -rf $CONTAINER_ROOT/root/sadm
  cp -r $SADM_ROOT_DIR $CONTAINER_ROOT/root/sadm

  container_snapshot $FUNCNAME
}

function stage_setup_sadm {
  echo_status "Start sadm setup script"

  container_run /root/sadm/install_scripts/setup_sadm.sh

  container_snapshot $FUNCNAME
}

function test_sadm {
  echo '[>] Test SADM... '

  test_file_present /root/sadm
}

function stage_setup_libprologin {
  echo_status 'Stage setup libprologin and SADM master secret'

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

function test_network {
  echo '[>] Test network... '

  echo -n '[>] Check IP '
  if ! machinectl status $CONTAINER_NAME | grep -q "Address: $CONTAINER_MAIN_IP"; then
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi
}

function test_local_network {
  echo '[>] Check SADM network '
  test_url http://mdb/call/query
}

function test_internet {
  echo '[>] Check internet access '
  test_url https://gstatic.com/generate_204
}

function stage_add_to_mdb {
  echo_status 'Register system into mdb'

  echo '[-] Get system mac address'
  mac_address=$(container_run_simple_verbose /usr/bin/ip link show host0 | grep ether | cut -f6 -d' ')
  if [[ -z $mac_address ]]; then
    echo >&2 "Could not get $CONTAINER_HOSTNAME MAC address"
    return 1
  fi

  # Delete existing record for the container
  (
    CONTAINER_NAME=$GW_CONTAINER_NAME
    CONTAINER_ROOT=/var/lib/machines/$CONTAINER_NAME

    echo '[-] Remove system from mdb (can terminate with status=1)'
    # Can fail if it's the first time we add this system to mdb
    container_run /var/prologin/venv/bin/python \
      /var/prologin/mdb/manage.py delmachine $CONTAINER_HOSTNAME || true

    echo '[-] Add system to mdb'
    container_run /var/prologin/venv/bin/python \
      /var/prologin/mdb/manage.py addmachine --hostname $CONTAINER_HOSTNAME \
      --mac $mac_address --ip $CONTAINER_MAIN_IP --rfs $MDB_RFS_ID \
      --hfs $MDB_HFS_ID --mtype $MDB_MACHINE_TYPE --room $MDB_ROOM \
      --aliases $MDB_ALIASES
  )
}

function stage_allow_root_ssh {
  echo_status 'Copy ssh credentials for root'

  mkdir -p $CONTAINER_ROOT/root/.ssh
  # root@gw.prolo can ssh to container, even if udbsync_rootssh is broken
  cat $CONTAINER_ROOT_GW/root/.ssh/id_rsa.pub \
    >> $CONTAINER_ROOT/root/.ssh/authorized_keys
  # root@container can ssh to gw.prolo
  cp $CONTAINER_ROOT_GW/root/.ssh/id_rsa $CONTAINER_ROOT/root/.ssh/id_rsa
}

function stage_setup_nginx {
  echo_status 'Stage setup nginx'

  container_run /usr/bin/pacman -S --noconfirm nginx

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

function stage_setup_postgresql {
  echo_status 'Stage setup postgresql'

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
  if container_run_quiet /usr/bin/psql -U postgres -c '\l'; then
    echo_ok "PASS"
  else
    echo_ko "FAIL"
    return 1
  fi
}

function stage_presencesync_sso {
  echo_status 'Install presencesync SSO'

  echo '[-] Configure presencesync SSO'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py presencesync_sso

  echo '[-] Enable and start the presencesync SSO service'
  container_run /usr/bin/systemctl enable --now presencesync_sso

  echo '[-] Reload nginx'
  container_run /usr/bin/systemctl reload nginx

  container_snapshot $FUNCNAME
}

function test_presencesync_sso {
  echo '[>] Test presencesync SSO... '

  test_service_is_enabled_active presencesync_sso
  sleep 3

  if container_run_verbose /usr/bin/curl -vs -o /dev/null http://mdb/ 2>&1 | grep -Fi 'X-SSO-Backend-Status: working'; then
    echo_ok "PASS"
  else
    echo_ko "FAIL"
    return 1
  fi
}
