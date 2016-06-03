#!/bin/sh

# Configure an Arch Linux system to be used by contestants and organizers.
# This script must be run chrooted inside the root NFS export

set -e

cd /root/sadm

echo '[+] Configure systemd-logind'
sed -e 's:^#KillUserProcesses=no:KillUserProcesses=yes:' \
    -e 's:^#KillExcludeUsers=root:KillExcludeUsers=root:' -i /etc/systemd/logind.conf

echo '[+] Generate host ssh keys'
ssh-keygen -A

echo '[+] Install packages for diskless boot'
pacman -Sy --needed --noconfirm mkinitcpio-nfs-utils nbd

echo '[+] Install packages we will configure'
pacman -Sy --needed --noconfirm sddm

echo '[+] Add initrd hooks and modules'
sed -e 's:^HOOKS.*:HOOKS="base udev autodetect modconf net block filesystems keyboard fsck prologin":g' \
    -e 's:^MODULES.*:MODULES="nfsv3 overlay":g' -i /etc/mkinitcpio.conf

echo '[+] Copy initrd configuration for diskless boot'
# TODO: use relative paths
cp rfs/initcpio/hooks/prologin /lib/initcpio/hooks/prologin
cp rfs/initcpio/install/prologin /lib/initcpio/install/prologin

echo '[+] Regenerate an initramfs for diskless boot'
mkinitcpio -p linux || true  # some hooks are really missing (e.g. fsck.brtfs)

echo '[+] Load nbd driver at startup'
echo nbd > /etc/modules-load.d/nbd.conf

echo '[+] Configure the system for SADM (setup_sadm.sh)'
./install_scripts/setup_sadm.sh

source /var/prologin/venv/bin/activate
python install.py libprologin
python install.py presenced
python install.py workernode
python install.py sddmcfg

echo '[+] Enable systemd services'
systemctl enable presenced sddm workernode

echo '[+] Disable systemd-networkd, use static IP from NFS boot'
systemctl disable systemd-networkd
