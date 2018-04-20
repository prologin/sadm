# Host
USE_BTRFS=true
SADM_ROOT_DIR=$(dirname $PWD)

# Container network
NETWORK_ZONE=prolo

# SADM secrets
ROOT_PASSWORD=101010
SADM_MASTER_SECRET=lesgerbillescesttropfantastique

# SADM MDB registration default values
MDB_ROOM=${MDB_ROOM:-pasteur}
MDB_MACHINE_TYPE=${MDB_MACHINE_TYPE:-service}
MDB_RFS_ID=${MDB_RFS_ID:-0}
MDB_HFS_ID=${MDB_HFS_ID:-0}
MDB_ALIASES=${MDB_ALIASES:-$CONTAINER_HOSTNAME}
