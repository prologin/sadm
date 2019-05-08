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

sed -i 's/^[#]IgnorePkg.*$/# Ignoring all of the following packages\
IgnorePkg = linux postgresql\*\
/' /etc/pacman.conf

curl https://repo.prologin.org/prologin.pub > /tmp/prologin.pub
pacman-key --add /tmp/prologin.pub
pacman-key --lsign-key prologin
rm /tmp/prologin.pub

echo '[+] Updating pacman database'
pacman -Sy

# Packages we expect to have installed on all the systems
echo '[+] Installing packages from the Arch Linux repositories'
pacman -S --needed --noconfirm base-devel git python python2 \
    libyaml libxslt postgresql-libs sqlite pwgen dnsutils \
    rsync tcpdump strace wget ethtool tree mtr iperf atop htop iotop iftop \
    nethogs jq tmux

echo '[+] Installing packages from the Prologin Arch Linux repository'
pacman -S --needed --noconfirm bash-eternal-history

echo '[+] Installing packages required for monitoring'
pacman -S --needed --noconfirm prometheus-node-exporter-git

echo '[+] Installing sadm'
mkdir -p /opt/prologin
python3 -m venv /opt/prologin/venv
/opt/prologin/venv/bin/pip install -r /root/sadm/requirements.txt

# Symlinks for backwards compatibility
mkdir -p /var/prologin
ln -s /opt/prologin/venv /opt/prologin/venv

echo '[+] sadm setup: all done!'
echo ''
echo 'You can now run:'
echo '  $ source /opt/prologin/venv/bin/activate'
echo 'and install the components needed'
