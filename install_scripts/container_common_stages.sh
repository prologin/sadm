source ./container_setup_config.sh

# Common setup stages
function stage_setup_container {
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
}

function stage_boostrap_arch_linux {
  echo_status "Bootstrap Arch Linux"

  ./bootstrap_arch_linux.sh $CONTAINER_ROOT ${CONTAINER_HOSTNAME}.prolo <(echo $ROOT_PASSWORD)

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

function stage_add_to_mdb {
  echo_status 'Register system into mdb'

  #TODO(halfr): use machinectl dbus method to get the MAC address?
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

    echo '[-] Remove system to mdb'
    # Can fail if it's the first time we add this system to mdb
    container_run /var/prologin/venv/bin/python \
      /var/prologin/mdb/manage.py delmachine $CONTAINER_HOSTNAME || true

    echo '[-] Add system to mdb'
    container_run /var/prologin/venv/bin/python \
      /var/prologin/mdb/manage.py addmachine --hostname $CONTAINER_HOSTNAME \
      --mac $mac_address --ip $CONTAINER_MAIN_IP --rfs 0 --hfs 0 \
      --mtype service --room pasteur --aliases $CONTAINER_ALIASES
  )

  echo '[-] Remove routes from the alien network'
  container_run_simple /usr/bin/ip route flush all
  echo '[-] Get new DHCP lease'
  container_run_simple /usr/bin/systemctl restart systemd-networkd
}

function stage_allow_root_ssh {
  echo_status 'Copy ssh credentials for root'

  mkdir -p $CONTAINER_ROOT/root/.ssh
  cat /var/lib/machines/$GW_CONTAINER_NAME/root/.ssh/id_rsa.pub \
    >> $CONTAINER_ROOT/root/.ssh/authorized_keys
}

function stage_setup_nginx {
  echo_status 'Stage setup nginx'

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
  if ! container_run_quiet /usr/bin/psql -U postgres -c '\l'; then
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi
}
