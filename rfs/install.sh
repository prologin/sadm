#!/bin/sh

set -e

echo -n 'First RHFS id (eg. 0, 2, 4, ...): ' && read rhfs_id

echo 'Detected disks:'
for disk in /dev/sd?; do
    fdisk -l "$disk" | grep Disk | grep bytes
done
while ! [ -b "${disk_0}" ]; do
    echo -n 'First disk (boot drive): ' && read disk_0
done
while ! [ -b "${disk_1}" ]; do
    echo -n 'Second disk (RAID slave): ' && read disk_1
done

rhfs_id_0=${rhfs_id}
rhfs_id_1=$((rhfs_id+1))
base_machine_name=rhfs${rhfs_id_0}${rhfs_id_1}

echo 'Summary'
echo '======='
echo "Machine name: ${base_machine_name}"
echo "Hosts RHFS ids: ${rhfs_id_0} ${rhfs_id_1}"
echo "Disks: ${disk_0} ${disk_1}"
echo
echo 'THIS WILL DELETE ALL THE DATA ON THESE DISKS'
echo -n 'Is this ok? (y/N) ' && read choice
[ "$choice" = 'y' ] || exit 1

# Check if we were put on the alien network. We will need internet access
# sooner or later.
if ! ip a | fgrep 'inet ' | fgrep -q 192.168.1.; then
    echo 'Machine not registered yet, please register it on mdb/ with:'
    echo
    echo "Hostnames: ${base_machine_name}.${rhfs_id_0}, ${base_machine_name}.${rhfs_id_1}"
    echo "MAC addresses:"
    ip l

    echo
    echo "Then reboot."

    exit 0
else
    echo 'Already on the service network, skipping registration.'
fi

echo 'Starting setup.'

echo 'Partitioning disks...'
for disk in "${disk_0}" "${disk_1}"; do
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

echo 'Creating RAID'
mdadm --create /dev/md0 --level=1 --metadata=1.2 --chunk=64 \
    --raid-devices=2 "${disk_0}2" "${disk_1}2"
cat /proc/mdstat

echo 'Creating LVM'
pvcreate /dev/md0
vgcreate data /dev/md0
lvcreate -L 15G data -n root
lvcreate -l 100%FREE data -n export

echo 'Formatting partitions'
mkfs.ext4 -L boot "${disk_0}1"
mkfs.ext4 -L root /dev/mapper/data-root
mkfs.ext4 -L export /dev/mapper/data-export

echo 'Mounting partitions'
mount /dev/mapper/data-root /mnt
mkdir /mnt/boot /mnt/export
mount /dev/disk/by-label/boot /mnt/boot
mount /dev/mapper/data-export /mnt/export

echo 'Installing the base system'
pacstrap /mnt base

echo 'Installing system and prologin-sadm dependencies'
pacstrap /mnt git python python-pip python-virtualenv libyaml dnsutils rsync \
    tcpdump base-devel libxslt ipset pssh syslinux ntp strace wget postgresql

echo 'Setting up the base system'
genfstab -p /mnt >> /mnt/etc/fstab
cp /etc/mdadm.conf /mnt/etc/mdadm.conf

cat >/mnt/var/tmp/install-2.sh <<EOF
#! /bin/bash

set -e

echo "${base_machine_name}" > /etc/hostname
ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime

echo 'Setting locale information'
echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen
echo 'LANG="en_US.UTF-8"' > /etc/locale.conf
locale-gen

echo 'Generating initrd'
sed -i 's/^HOOKS=.*$/HOOKS="base udev autodetect modconf block mdadm_udev lvm2 filesystems keyboard fsck"/' /etc/mkinitcpio.conf
mkinitcpio -p linux

echo 'Enabling services'
systemctl enable dhcpcd
systemctl enable sshd
systemctl enable ntpd

echo 'Changing password'
echo "root:changeme" | chpasswd

echo 'Installing bootloader'
syslinux-install_update -i -a -m
sed -i s@/dev/sda3@LABEL=root@ /boot/syslinux/syslinux.cfg

echo 'Setting up sadm'
mkdir /var/prologin
virtualenv3 --no-site-packages /var/prologin/venv
source /var/prologin/venv/bin/activate
cd /root
git clone http://bitbucket.org/prologin/sadm.git
cd sadm
export C_INCLUDE_PATH=/usr/include/libxml2 # fix for archlinux
pip install -r requirements.txt
EOF
chmod +x /mnt/var/tmp/install-2.sh
echo 'Chrooting'
arch-chroot /mnt /var/tmp/install-2.sh

echo 'Unmounting'
umount /mnt{/boot,/export,}

echo 'Press enter to reboot (unplug the USB drive before next boot)'
read
reboot
