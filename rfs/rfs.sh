#!/bin/bash

# Configure a new Arch Linux to be used by contestants and organizers.

# This script is executed *chrooted in an nfsroot* during the 'install.py rfs'
# process.

set -e

echo 'Setting timezone'
ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime
echo '[Time]
NTP=ntp.prolo' > /etc/systemd/timesyncd.conf

echo 'Setting locales'
sed -e 's:^#en_US:en_US:g' -e 's:^#fr_FR:fr_FR:g' -i /etc/locale.gen
locale-gen
echo LANG=en_US.UTF-8 > /etc/locale.conf
echo KEYMAP=us > /etc/vconsole.conf

echo 'Setting pacman'
sed -e 's:^CheckSpace:#CheckSpace:' -e 's:^SigLevel.*:SigLevel = Never:' -i /etc/pacman.conf

echo 'Generating host ssh keys'
ssh-keygen -A

echo 'Setting root password'
echo 'root:changeme' | chpasswd

echo 'Adding initrd hooks and modules'
sed -e 's:^HOOKS.*:HOOKS="base udev autodetect modconf net block filesystems keyboard fsck prologin":g' \
    -e 's:^MODULES.*:MODULES="nfsv3":g' -i /etc/mkinitcpio.conf
echo 'Regenerating an initramfs in order to include the prologin hook'
mkinitcpio -p linux

echo 'Install the prologin virtualenv and library'
mkdir /var/prologin
virtualenv3 /var/prologin/venv
source /var/prologin/venv/bin/activate
cd /sadm
pip install -r requirements.txt
python install.py libprologin
# And some sadm services
python install.py presenced set_hostname

echo 'Enable some services'
systemctl enable sshd presenced set_hostname kdm
