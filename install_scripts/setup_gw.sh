#!/bin/bash

# Install gw.prolo

set -e

echo '[+] Installing packages from the Arch Linux repositories'
pacman -S --needed --noconfirm dhcp bind sqlite ipset postgresql nbd \
    tftp-hpa conntrack-tools

echo '[+] Installing packages from the Prologin Arch Linux repository'
pacman -S --needed --noconfirm openresty ipxe-sadm-git
