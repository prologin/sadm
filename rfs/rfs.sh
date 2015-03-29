#!/bin/bash

# Configure a new Arch Linux to be used by contestants and organizers.

# This script is executed *chrooted in an nfsroot* during the 'install.py rfs'
# process.

set -e

# Usual basic setup
ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime

sed -e 's:^#en_US:en_US:g' -e 's:^#fr_FR:fr_FR:g' -i /etc/locale.gen
locale-gen

sed -e 's:^HOOKS.*:HOOKS="base udev autodetect modconf net block filesystems keyboard fsck prologin":g' \
    -e 's:^MODULES.*:MODULES="nfsv3":g' -i /etc/mkinitcpio.conf
sed -e 's:^CheckSpace:#CheckSpace:' -e 's:^SigLevel.*:SigLevel = Never:' -i /etc/pacman.conf
echo LANG=en_US.UTF-8 > /etc/locale.conf
echo KEYMAP=us > /etc/vconsole.conf

echo '[Time]
NTP=ntp.prolo' > /etc/systemd/timesyncd.conf

ssh-keygen -A

# Regenerate an initramfs in order to include the prologin hook
mkinitcpio -p linux

# Install the prologin virtualenv and library
mkdir /var/prologin
virtualenv3 /var/prologin/venv
source /var/prologin/venv/bin/activate
cd /sadm
pip install -r requirements.txt
python install.py libprologin
# And some sadm services
python install.py presenced set_hostname

# Enable some services
systemctl enable sshd presenced set_hostname kdm
