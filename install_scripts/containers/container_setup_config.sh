USE_BTRFS=true
DEBUG=${DEBUG:-true}

# Container network name
NETWORK_ZONE=prolo

# SADM secrets
ROOT_PASSWORD=101010
SADM_MASTER_SECRET=lesgerbillescesttropfantastique

if $DEBUG; then
  set -x
fi
