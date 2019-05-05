USE_BTRFS=true
DEBUG=${DEBUG:-true}

# Container network name
NETWORK_ZONE=prolo

# SADM secrets
ROOT_PASSWORD=101010
SADM_MASTER_SECRET=lesgerbillescesttropfantastique

ARCH_LINUX_BASE_ROOT=/var/lib/machines/arch_linux_base

# Do not edit below
if $DEBUG; then
  set -x
fi
