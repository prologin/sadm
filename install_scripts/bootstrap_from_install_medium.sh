#!/bin/bash

# Run this script if you are installing from an Arch Linux install media.
# It does a standalone clone and setup of sadm from the main git repository. If
# you are developping on SADM, directly use install_scripts/setup_sadm.sh

REPO_URL=https://github.com/prologin/sadm
BRANCH=master

if mount | grep --quiet archiso; then
  # When running on the Arch Linux install media, increase the overlay work dir
  # size
  echo '[+] Increasing the size of /run/archiso/cowspace'
  mount -o remount,size=2G /run/archiso/cowspace
fi

echo '[+] Installing dependencies'
pacman -Sy --needed --noconfirm git

echo '[+] Cloning sadm'
cd /root
git clone --branch $BRANCH $REPO_URL sadm

echo '[+] Starting Arch Linux bootstrap script'
( cd ./sadm/install_scripts; /bootstrap_arch_linux_raid1.sh )

echo '[+] Copying SADM install'
cp -r sadm /mnt/root/sadm
