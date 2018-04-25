#!/bin/bash

# Install mon.prolo

set -e

echo '[+] Installing packages from the Arch Linux repositories'
pacman -S --needed --noconfirm grafana


echo '[+] Installing packages from the Prologin Arch Linux repository'
pacman -S --needed --noconfirm prometheus
