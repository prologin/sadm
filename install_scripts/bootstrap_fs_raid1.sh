#!/bin/bash

# This script installs a base Arch Linux system. It should be run with
# completely virgin disks. If they are not, then you may want to use some of
# these comamnds:
# vgremove vgname
# pvremove pvname
# mdadm --stop /dev/md127
# mdadm --zero-superblock /dev/vda2

set -e

USAGE_STRING="usage: $0 hostname /dev/first/disk /dev/second/disk"

base_machine_name="${1?$USAGE_STRING}"
disk_0="${2?$USAGE_STRING}"
disk_1="${3?$USAGE_STRING}"

# Disk and partitions names
md_name="$base_machine_name"
pv="/dev/md/$md_name"
vg="${base_machine_name}"
fs_boot="${base_machine_name}boot"
fs_root="${base_machine_name}root"

echo 'Summary'
echo '======='
echo
echo "Machine name: ${base_machine_name}"
echo "Disks: boot: ${disk_0}"
echo "Disks: secondary: ${disk_1}"
echo "RAID1: device name: $md_name"
echo "LVM: pv: $pv"
echo "LVM: vg: $vg"
echo "Filesystems: boot: /dev/disks/by-label/$fs_boot"
echo "Filesystems: root: /dev/disks/by-label/$fs_root"
echo
echo 'THIS WILL DELETE ALL THE DATA ON THESE DISKS'
echo -n 'Is this ok? (y/N) ' && read choice
[ "$choice" = 'y' ] || exit 1

echo '[+] Starting setup.'

echo '[+] Partitioning disks...'
for disk in "$disk_0" "$disk_1"; do
echo "o
n
p
1

+250M
n
p
2


w" | fdisk "$disk"
done

echo '[+] Creating RAID'
mdadm --create "$md_name" --level=1 --metadata=1.2 --chunk=64 \
    --raid-devices=2 "${disk_0}2" "${disk_1}2"
cat /proc/mdstat

echo '[+] Creating LVM'
pvcreate "$pv"
vgcreate "$vg" "$pv"
lvcreate -l 100%FREE "$vg" -n "$fs_root"

echo '[+] Formatting partitions'
mkfs.ext4 -O ^64bit -L "$fs_boot" "${disk_0}1"
mkfs.ext4 -L "$fs_root" "/dev/mapper/${vg}-$fs_root"

echo '[+] Mounting partitions'
mount "/dev/mapper/${vg}-$fs_root" /mnt
mkdir /mnt/boot
mount "/dev/disk/by-label/$fs_boot" /mnt/boot
