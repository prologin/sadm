#!/bin/bash

# This script is executed *chrooted in an nfsroot* during the 'install.py rfs'
# process.

set -e

# Usual basic setup
ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime
sed -e 's:^#en_US:en_US:g' -e 's:^#fr_FR:fr_FR:g' -i /etc/locale.gen
sed -e 's:^HOOKS.*:HOOKS="base udev autodetect modconf net block filesystems keyboard fsck prologin":g' \
    -e 's:^MODULES.*:MODULES="nfsv3":g' -i /etc/mkinitcpio.conf
sed -e 's:^CheckSpace:#CheckSpace:' -e 's:^SigLevel.*:SigLevel = Never:' -i /etc/pacman.conf
sed -e 's:^After=(.*):After=$1 set_hostname.service:' -i /usr/lib/systemd/system/collectd.service
echo LANG=en_US.UTF-8 > /etc/locale.conf
echo KEYMAP=us > /etc/vconsole.conf
locale-gen
ssh-keygen -A

# Regenerate an initramfs in order to include the prologin hook
mkinitcpio -p linux

# Install the prologin virtualenv and library
mkdir /var/prologin
virtualenv3 --no-site-packages /var/prologin/venv
source /var/prologin/venv/bin/activate
cd /sadm
pip install -r requirements.txt
python install.py libprologin
# And some sadm services
python install.py presenced set_hostname

# Enable some services
for svc in {sshd,ntpd,presenced,set_hostname,collectd,kdm}.service; do
  systemctl enable "$svc"
done
