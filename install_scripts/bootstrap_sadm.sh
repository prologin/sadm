#!/bin/bash

# This script does a standalone clone and setup of sadm from the main git
# repository. If you are developping on SADM, directly use
# install_scripts/setup_sadm.sh

if mount | grep --quiet archiso; then
  # When running on the Arch Linux install media, increase the overlay work dir
  # size
  echo '[+] Increasing the size of /run/archiso/cowspace'
  mount -o remount,size=2G /run/archiso/cowspace
fi

echo '[+] Installing dependencies'
pacman -S --needed --noconfirm git

echo '[+] Cloning sadm'
cd /root
git clone https://github.com/prologin/sadm.git

echo '[+] Starting sadm setup script'
cd sadm
./install_scripts/setup_sadm.sh
