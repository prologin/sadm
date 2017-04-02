#!/bin/sh

# Configure an Arch Linux system to be used by contestants and organizers.
# This is not a server setpu

set -e

echo 'Setting systemd-logind'
sed -e 's:^#KillUserProcesses=no:KillUserProcesses=yes:' \
    -e 's:^#KillExcludeUsers=root:KillExcludeUsers=root:' -i /etc/systemd/logind.conf

echo 'Setting pacman'
sed -e 's:^CheckSpace:#CheckSpace:' -e 's:^SigLevel.*:SigLevel = Never:' -i /etc/pacman.conf

echo 'Generating host ssh keys'
ssh-keygen -A

echo 'Adding initrd hooks and modules'
sed -e 's:^HOOKS.*:HOOKS="base udev autodetect modconf net block filesystems keyboard fsck prologin":g' \
    -e 's:^MODULES.*:MODULES="nfsv3":g' -i /etc/mkinitcpio.conf
echo 'Regenerating an initramfs in order to include the prologin hook'
mkinitcpio -p linux

echo 'Load nbd driver at startup'
echo nbd > /etc/modules-load.d/nbd.conf

echo 'Install the prologin virtualenv and library'

./setup_sadm.sh

cd /root/sadm
python install.py libprologin
python install.py presenced

echo 'Enable some services'
systemctl enable presenced sddm

echo 'rfs: all done!'
