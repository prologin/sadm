#!/bin/bash

# Errors are fatal
set -e

# Configure a RFS server

echo '[+] Installing base packages for rfs'
pacman -Sy --needed --noconfirm arch-install-scripts nfs-utils nbd
