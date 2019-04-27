#!/bin/bash

# Install web.prolo

set -e

echo '[+] Installing packages from the Arch Linux repositories'
pacman -S --needed --noconfirm ipset postgresql nginx
