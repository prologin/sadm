#!/bin/sh

# Configure an Arch Linux system to be used by contestants and organizers.
# This script must be run chrooted inside the root NFS export

set -e

echo '[+] Configure systemd-logind'
sed -e 's:^#KillUserProcesses=no:KillUserProcesses=yes:' \
    -e 's:^#KillExcludeUsers=root:KillExcludeUsers=root:' -i /etc/systemd/logind.conf

echo '[+] Generate host ssh keys'
ssh-keygen -A

echo '[+] Add initrd hooks and modules'
sed -e 's:^HOOKS.*:HOOKS="base udev autodetect modconf block filesystems keyboard fsck prologin":g' \
    -e 's:^MODULES.*:MODULES="nfsv3":g' -i /etc/mkinitcpio.conf

echo '[+] Regenerate an initramfs with SADM configuration'
mkinitcpio -p linux

echo '[+] Load nbd driver at startup'
echo nbd > /etc/modules-load.d/nbd.conf

echo '[+] Configure the system for SADM (setup_sadm.sh)'
./setup_sadm.sh

source /var/prologin/venv/bin/activate
python install.py libprologin
python install.py presenced
python install.py sddmcfg

echo 'Enable some services'
systemctl enable presenced sddm
