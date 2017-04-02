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
