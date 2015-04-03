#! /bin/bash

# This script installs a base Arch Linux system. It should be run with
# completely virgin disks.

set -e

echo 'Detected disks:'
for disk in /dev/vd?; do
    fdisk -l ${disk} | grep Disk | grep bytes
done
while ! [ -b "${disk_0}" ]; do
    echo -n 'First disk (boot drive): ' && read disk_0
done
while ! [ -b "${disk_1}" ]; do
    echo -n 'Second disk (RAID slave): ' && read disk_1
done

base_machine_name=gw

echo 'Summary'
echo '======='
echo "Machine name: ${base_machine_name}"
echo "Disks: ${disk_0} ${disk_1}"
echo
echo 'THIS WILL DELETE ALL THE DATA ON THESE DISKS'
echo -n 'Is this ok? (y/N) ' && read choice
[ "$choice" = 'y' ] || exit 1

echo 'Starting setup.'

echo 'Partitioning disks...'
for disk in ${disk_0} ${disk_1}; do
echo "o
n
p
1

+250M
n
p
2


w" | fdisk ${disk}
done

echo 'Creating RAID'
mdadm --create /dev/md0 --level=1 --metadata=1.2 --chunk=64 \
    --raid-devices=2 ${disk_0}2 ${disk_1}2
cat /proc/mdstat

echo 'Creating LVM'
pvcreate /dev/md0
vgcreate data /dev/md0
lvcreate -l 100%FREE data -n root

echo 'Formatting partitions'
mkfs.ext4 -L boot ${disk_0}1
mkfs.ext4 -L root /dev/mapper/data-root

echo 'Mounting partitions'
mount /dev/mapper/data-root /mnt
mkdir /mnt/boot
mount /dev/disk/by-label/boot /mnt/boot

echo 'Installing base system and prologin-sadm dependencies'
pacstrap /mnt base base-devel syslinux \
    git python python-pip python-virtualenv libyaml libxslt postgresql-libs \
    dhcp bind nginx sqlite postgresql-libs pwgen ipset postgresql nbd tftp-hpa \
    openssh dnsutils rsync tcpdump strace wget ethtool atop htop

echo 'Setting up the base system'
genfstab -p /mnt >> /mnt/etc/fstab

cat >/mnt/var/tmp/install-2.sh <<EOF
#! /bin/bash

set -e

echo 'Setting hostname'
echo ${base_machine_name} > /etc/hostname

echo 'Setting timezone'
ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime

echo 'Setting locale information'
echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen
echo 'LANG="en_US.UTF-8"' > /etc/locale.conf
locale-gen

echo 'Generating initrd'
sed -i 's/^HOOKS=.*$/HOOKS="base udev autodetect modconf block mdadm_udev lvm2 filesystems keyboard fsck"/' /etc/mkinitcpio.conf
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
git clone http://bitbucket.org/halfr/sadm.git
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
