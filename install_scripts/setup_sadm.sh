#!/bin/bash

# Install common SADM setup for all systems

set -e

echo '[+] Installing the prologin Arch Linux repository'
if ! grep -F '[prologin]' /etc/pacman.conf >/dev/null; then
  cat >>/etc/pacman.conf <<EOF
[prologin]
Server = https://repo.prologin.org/
EOF
fi

curl https://repo.prologin.org/prologin.pub > /tmp/prologin.pub
pacman-key --add /tmp/prologin.pub
pacman-key --lsign-key prologin
rm /tmp/prologin.pub

echo '[+] Updating pacman database'
pacman -Sy

# Packages we expect to have installed on all the systems
echo '[+] Installing packages from the Arch Linux repositories'
pacman -S --needed --noconfirm base-devel git python python2 python-pip \
    python-virtualenv libyaml libxslt postgresql-libs sqlite postgresql-libs \
    pwgen dnsutils rsync tcpdump strace wget ethtool tree mtr iperf atop htop \
    iotop iftop nethogs jq tmux

echo '[+] Installing packages from the Prologin Arch Linux repository'
pacman -S --needed --noconfirm bash-eternal-history

echo '[+] Installing packages required for monitoring'
pacman -S --needed --noconfirm prometheus-node-exporter-git

echo '[+] Installing sadm'
mkdir -p /var/prologin
virtualenv3 /var/prologin/venv
source /var/prologin/venv/bin/activate
pip install -r /root/sadm/requirements.txt

echo '[+] sadm setup: all done!'
echo ''
echo 'You can now run:'
echo '  $ source /var/prologin/venv/bin/activate'
echo 'and install the components needed'
