#!/bin/bash

# This script installs a base Arch Linux system. It should be run with
# completely virgin disks.

set -e
shopt -s nullglob

./common_pre.sh

base_machine_name=misc

echo 'Detected disks:'
for disk in /dev/vd? /dev/sd?; do
    fdisk -l ${disk} | grep Disk | grep bytes
done
while ! [ -b "$disk_0" ]; do
    echo -n 'Disk (boot drive): ' && read disk_0
done

echo 'Summary'
echo '======='
echo "Machine name: ${base_machine_name}"
echo "Disk: ${disk_0}"
echo
echo 'THIS WILL DELETE ALL THE DATA ON THESE DISKS'
echo -n 'Is this ok? (y/N) ' && read choice
[ "$choice" = 'y' ] || exit 1

echo 'Starting setup.'

echo 'Partitioning disks...'
echo "o
n
p
1

+250M
n
p
2


w" | fdisk "$disk_0"

echo 'Creating LVM'
pvcreate "${disk_0}2"
vgcreate data "${disk_0}2"
lvcreate -l 100%FREE data -n root

echo 'Formatting partitions'
mkfs.ext4 -L boot "${disk_0}1"
mkfs.ext4 -L root /dev/mapper/data-root

echo 'Mounting partitions'
mount /dev/mapper/data-root /mnt
mkdir /mnt/boot
mount /dev/disk/by-label/boot /mnt/boot

echo 'Installing base system and prologin-sadm dependencies'
pacstrap /mnt base base-devel syslinux \
    git python python-pip python-virtualenv libyaml libxslt postgresql-libs \
    sqlite pwgen ipset postgresql \
    openssh dnsutils rsync tcpdump strace wget ethtool atop htop

echo 'Setting up the base system'
genfstab -p /mnt >> /mnt/etc/fstab

cat >/mnt/var/tmp/install-2.sh <<EOF
#! /bin/bash

set -e

echo 'Setting hostname'
echo "${base_machine_name}" > /etc/hostname

echo 'Setting timezone'
ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime

echo 'Setting locale information'
echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen
echo 'LANG="en_US.UTF-8"' > /etc/locale.conf
locale-gen

echo 'Setting ntp'
echo '[Time]
NTP=ntp.prolo' > /etc/systemd/timesyncd.conf

echo 'Setting network settings'
echo '[Match]
Name=*

[Network]
DHCP=yes

[DHCP]
# "Most routers will send garbage, so make this opt-in only."
# systemd 1bd27a45d04639190fc91ad2552b72ea759c0c27
UseDomains=yes' > /etc/systemd/network/dhcp.network

echo 'Generating initrd'
sed -i 's/^HOOKS=.*$/HOOKS="base udev autodetect modconf block lvm2 filesystems keyboard fsck"/' /etc/mkinitcpio.conf
mkinitcpio -p linux

echo 'Enabling services'
systemctl enable sshd

echo 'Changing password'
echo "root:changeme" | chpasswd

echo 'Setting bash history'
echo '#!/usr/bin/env bash

export HISTTIMEFORMAT="%d/%m/%y %T "
export HISTSIZE=-1
export HISTFILESIZE=-1
export HISTFILE=~/.bash_eternal_history
export PROMPT_COMMAND="history -a"' > /etc/profile.d/history.sh
chmod +x /etc/profile.d/history.sh

echo 'Installing bootloader'
syslinux-install_update -i -a -m
sed -i s@/dev/sda3@LABEL=root@ /boot/syslinux/syslinux.cfg

echo 'Setting up sadm'
mkdir /var/prologin
virtualenv3 /var/prologin/venv
source /var/prologin/venv/bin/activate
cd /root
git clone http://bitbucket.org/prologin/sadm.git
cd sadm
pip install -r requirements.txt
EOF

chmod +x /mnt/var/tmp/install-2.sh
echo 'Chrooting'
arch-chroot /mnt /var/tmp/install-2.sh

echo 'Unmounting'
umount /mnt{/boot,}

echo 'Press enter to reboot (unplug the USB drive, if any)'
read
reboot
