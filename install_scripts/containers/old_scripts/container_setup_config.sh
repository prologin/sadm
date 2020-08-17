config_file="$( dirname $0 )/container_setup.conf"
if [ -f "$config_file" ]; then
    source "$config_file";
fi

USE_BTRFS=${USE_BTRFS:-true}
DEBUG=${DEBUG:-true}

# Container network name
NETWORK_ZONE=prolo

# SADM secrets
ROOT_PASSWORD=101010
SADM_MASTER_SECRET=lesgerbillescesttropfantastique

# Do not edit below
if $DEBUG; then
  set -x
fi
