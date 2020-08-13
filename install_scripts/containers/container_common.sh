set -e  # Fail fast

source ../common.sh

config_file="$( dirname $0 )/container_setup.conf"
if [ -f "$config_file" ]; then
    source "$config_file";
fi

USE_BTRFS=${USE_BTRFS:-true}
DEBUG=${DEBUG:-true}
if test -z "$SSH_PUB_KEY"; then
    echo_ko "Error: SSH_PUB_KEY path not defined in config file"
    exit 1
fi

# Container network name
NETWORK_ZONE=prolo

# Root password
ROOT_PASSWORD=101010

if $DEBUG; then
  set -x
fi

SADM_ROOT_DIR=$(readlink -f -- $PWD/../..)
ANSIBLE_INVENTORY="$SADM_ROOT_DIR/ansible/inventory"

ARCH_LINUX_BASE_ROOT=/var/lib/machines/arch_linux_base
CONTAINER_ROOT=/var/lib/machines/$CONTAINER_NAME

function container_remove_btrfs_root {
  # 1) Delete nested subvolumes in container
  # When started on a btrfs rootfs, systemd creates subvolumes on these
  # directories, which we have to delete before deleting the container root
  # subvolume.
  for subdir in machines portables; do
    # This can fail if we restored a snapshot.
    btrfs 2>/dev/null subvolume delete $CONTAINER_ROOT/var/lib/$subdir || true
  done
  # 2) Delete root container subvolume
  btrfs subvolume delete $CONTAINER_ROOT
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
  echo_status "Spawn container"
  machinectl start $CONTAINER_NAME

  echo "[-] Wait for machine D-Bus socket to be ready"
  until systemd-run --quiet --pipe -M "$CONTAINER_NAME" /bin/true 2>/dev/null; do
      sleep 1;
  done

  echo '[-] Containers on this system:'
  machinectl list

  echo "[-] You can now login to $CONTAINER_NAME as root:$ROOT_PASSWORD using:"
  echo "  # machinectl login $CONTAINER_NAME"
}

# Script directives
function skip {
  # do nothing
  echo_status "Skip: $*"
}

function run {
  $*
}
