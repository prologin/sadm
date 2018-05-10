#!/bin/bash

set -e

USAGE_STRING="usage: $0 hostname /dev/main/disk"

base_machine_name="${1?$USAGE_STRING}"
disk="${2?$USAGE_STRING}"

# Disk and partitions names
fs_boot="${base_machine_name}boot"
fs_root="${base_machine_name}root"

echo 'Summary'
echo '======='
echo
echo "Machine name: ${base_machine_name}"
echo "Disk: : ${disk}"
echo "Filesystems: boot: /dev/disks/by-label/$fs_boot"
echo "Filesystems: root: /dev/disks/by-label/$fs_root"
echo
echo 'THIS WILL DELETE ALL THE DATA ON THIS DISKS'
echo -n 'Is this ok? (y/N) ' && read choice
[ "$choice" = 'y' ] || exit 1

echo '[+] Starting setup.'

echo '[+] Partitioning disk...'

echo "o
n
p
1

+250M
n
p
2


w" | fdisk -w always -W always "$disk"

echo '[+] Formatting partitions'
mkfs.ext4 -O ^64bit -L "$fs_boot" "${disk}1"
mkfs.ext4 -L "$fs_root" "${disk}2"

echo '[+] Mounting partitions'
mount "${disk}2" /mnt
mkdir /mnt/boot
mount "${disk}1" /mnt/boot
