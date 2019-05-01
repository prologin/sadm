cd $(dirname -- $0)

source ../common.sh

this_script_must_be_run_as_root

if [[ -z $CONTAINER_NAME || -z $GW_CONTAINER_NAME ]]; then
  echo >&2 "Please define \$CONTAINER_NAME and \$GW_CONTAINER_NAME before sourcing this script"
  exit 1
fi

source ./container_setup_config.sh

# Root directory of this sadm install
SADM_ROOT_DIR=$(readlink -f -- $PWD/../..)

# SADM MDB registration default values
MDB_ROOM=${MDB_ROOM:-pasteur}
MDB_MACHINE_TYPE=${MDB_MACHINE_TYPE:-service}
MDB_RFS_ID=${MDB_RFS_ID:-0}
MDB_HFS_ID=${MDB_HFS_ID:-0}
MDB_ALIASES=${MDB_ALIASES:-$CONTAINER_HOSTNAME}

# Other container-related variables
CONTAINER_ROOT=/var/lib/machines/$CONTAINER_NAME
CONTAINER_ROOT_GW=/var/lib/machines/$GW_CONTAINER_NAME

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

    echo_status "Snapshot to $snapshot_root"

    if [ -d $snapshot_root ]; then
      # remove existing snapshot
      btrfs subvolume delete $snapshot_root
    fi
    # make the read-only snapshot
    btrfs subvolume snapshot -r $CONTAINER_ROOT $snapshot_root
  fi
}

function container_stop {
  echo_status "Stop container"
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
  echo_status "Spawn container with 5 seconds delay to have systemd start"
  machinectl start $CONTAINER_NAME && sleep 5

  echo '[-] Containers on this system:'
  machinectl list

  echo "[-] You can now login to $CONTAINER_NAME as root:$ROOT_PASSWORD using:"
  echo "  # machinectl login $CONTAINER_NAME"
}

function container_run_simple {
  systemd-run -M $CONTAINER_NAME --pipe "$@" >/dev/null
}

function container_run_simple_verbose {
  systemd-run -M $CONTAINER_NAME --pipe "$@"
}

function container_run {
  # PATH is configured for the python virtualenv
  systemd-run -M $CONTAINER_NAME --wait \
    --property WorkingDirectory=/root/sadm \
    --setenv=PATH=/var/prologin/venv/bin:/usr/bin \
    "$@"
}

function container_run_verbose {
  # PATH is configured for the python virtualenv
  systemd-run -M $CONTAINER_NAME --wait --pipe \
    --property WorkingDirectory=/root/sadm \
    --setenv=PATH=/var/prologin/venv/bin:/usr/bin \
    "$@"
}

function container_run_quiet {
  # PATH is configured for the python virtualenv
  systemd-run --quiet -M $CONTAINER_NAME --wait --pipe \
    --property WorkingDirectory=/root/sadm \
    --setenv=PATH=/var/prologin/venv/bin:/usr/bin \
    "$@"
}

# Script directives
function skip {
  # do nothing
  echo_status "Skip: $*"
}

function run {
  $*
}

function restore {
  snapshot_name=$1
  snapshot_root=${CONTAINER_ROOT}_$snapshot_name

  if $USE_BTRFS; then
    echo_status "Snapshot restore of $snapshot_root"
    container_stop

    if [ -d $CONTAINER_ROOT ]; then
      # Remove existing container root:
      # 1) Delete nested subvolumes in container
      # When started on a btrfs rootfs, systemd creates subvolumes on these
      # directories, which we have to delete before deleting the container root
      # subvolume.
      btrfs 2>/dev/null subvolume delete $CONTAINER_ROOT/var/lib/machines || true  # this can fail if we restored a snapshot
      btrfs 2>/dev/null subvolume delete $CONTAINER_ROOT/var/lib/portables || true  # this can fail if we restored a snapshot
      # 2) Delete root container subvolume
      btrfs subvolume delete $CONTAINER_ROOT
    fi
    # restore the snapshot as read+write
    btrfs subvolume snapshot $snapshot_root $CONTAINER_ROOT

    container_start
  fi
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

function test_file_present {
  filename=$1
  echo -n "[>] $filename is "
  if [[ -e "$CONTAINER_ROOT/$filename" ]]; then
    echo_ok "present"
  else
    echo_ko "absent"
    return 1
  fi
}

function test_file_present_not_empty {
  filename=$1
  echo -n "[>] $filename is "
  if [[ -s "$CONTAINER_ROOT/$filename" ]]; then
    echo_ok "present, not empty"
  else
    if [[ -e "$CONTAINER_ROOT/$filename" ]]; then
      echo_ko "present, empty"
      return 1
    else
      echo_ko "absent"
      return 1
    fi
  fi
}

function test_url {
  URL=$1

  echo "[>] Check $URL "
  if ! container_run /usr/bin/curl --fail $URL; then
    container_run /usr/bin/curl $URL || true
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi
}

source ./container_common_stages.sh
