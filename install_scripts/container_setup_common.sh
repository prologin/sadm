if [[ -z $CONTAINER_NAME ]]; then
  echo >&2 "Please define $$CONTAINER_NAME before sourcing this script"
  exit 1
fi

USE_BTRFS=true
SADM_ROOT_DIR=$(dirname $PWD)

# Secrets
ROOT_PASSWORD=101010
SADM_MASTER_SECRET=lesgerbillescesttropfantastique

# Other container-related variables
NETWORK_ZONE=prolo
CONTAINER_ROOT=/var/lib/machines/$CONTAINER_NAME

function container_script_header {
  cat <<EOF
[+] Welcome to the container setup of SADM!
[+] Container name: $CONTAINER_NAME
[+] Container network zone: $NETWORK_ZONE
[+] Container root: $CONTAINER_ROOT
EOF
}

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

function container_run_simple {
  # Send dummy input else systemd-run will wait for user input
  systemd-run -M $CONTAINER_NAME --wait "$@"
}

function container_run {
  # PATH is configured for the python virtualenv
  # Send dummy input else systemd-run will wait for user input
  systemd-run -M $CONTAINER_NAME --wait \
    --property WorkingDirectory=/root/sadm \
    --setenv=PATH=/var/prologin/venv/bin:/usr/bin \
    "$@"
}

function container_run_verbose {
  # PATH is configured for the python virtualenv
  # Send dummy input else systemd-run will wait for user input
  systemd-run -M $CONTAINER_NAME --wait --quiet --pty \
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

# Common setup stages
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

  echo "[-] Disable DHCP server for our network zone"
  cat >/etc/systemd/network/80-container-vz-prolo.network <<EOF
[Match]
Name=vz-$NETWORK_ZONE
Driver=bridge

[Network]
# Default to using a /24 prefix, giving up to 253 addresses per virtual network.
Address=0.0.0.0/24
LinkLocalAddressing=yes
IPMasquerade=yes
LLDP=yes
EmitLLDP=customer-bridge
EOF

  echo "[-] Restart systemd-networkd"
  systemctl restart systemd-networkd

  container_snapshot $FUNCNAME
}

function stage_boostrap_arch_linux {
  ./bootstrap_arch_linux.sh $CONTAINER_ROOT $CONTAINER_HOSTNAME ./plaintext_root_pass

  container_snapshot $FUNCNAME
}

function stage_setup_sadm {
  echo "[+] Copy $SADM_ROOT_DIR to the container"
  cp -r $SADM_ROOT_DIR $CONTAINER_ROOT/root/sadm

  echo "[-] Start sadm setup script"
  container_run /root/sadm/install_scripts/setup_sadm.sh

  container_snapshot $FUNCNAME
}

function test_sadm {
  echo '[>] Test SADM... '

  echo '[>] sadm directory exists'
  container_run_quiet /usr/bin/test -d /root/sadm
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
