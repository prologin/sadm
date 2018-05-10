#!/bin/bash

set -e

# Get args
base_machine_name=${1?usage: $0 hostname}

echo '[+] This script configures a Arch Linux system boot for BIOS'

genfstab -L -p /mnt >> /mnt/etc/fstab

echo '[+] Generating initrd'
arch-chroot /mnt mkinitcpio -p linux

echo '[+] Installing bootloader'
pacstrap /mnt syslinux
arch-chroot /mnt syslinux-install_update -i -a -m
sed -i "s@/dev/sda3@LABEL=${base_machine_name}root@" /mnt/boot/syslinux/syslinux.cfg
