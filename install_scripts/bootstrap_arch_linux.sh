#!/bin/bash

# Set current working directory
cd $(dirname -- $0)

# Get shared functions
source ./common.sh

# Configuration
SADM_LOCALE='en_US.UTF-8'
SADM_CHARSET='UTF-8'
SADM_TIMEZONE='Europe/Paris'

# Arch Linux install
ARCH_MIRROR=http://archlinux.mirrors.ovh.net/archlinux
# Release used for bootstraping from a non-Arch Linux system
ARCH_RELEASE_DATE=2018.06.01
# Mirror list to use in case we don't have access to pacstrap
MIRRORLIST_URL="https://www.archlinux.org/mirrorlist/?country=FR&protocol=https&ip_version=4&ip_version=6&use_mirror_status=on"

# Usage
if [ $# -ne 3 ]; then
    echo >&2 "Usage: $0 ROOT_DIR HOSTNAME PLAINTEXT_ROOT_PASSWORD_FILE"
    echo >&2 ""
    echo >&2 "Install and configure Arch Linux in the ROOT_DIR folder."
    echo >&2 "Example (as root):"
    echo >&2 "  $ echo my_root_password_is_pretty_long > plaintext_root_pass"
    echo >&2 "  $ mkdir root_dir"
    echo >&2 "  $ ./bootstrap_arch_linux.sh ./root_dir hostname ./plaintext_root_pass"
    exit 1
fi

# Requirements checks
if test -e /etc/arch-release && ! which arch-chroot >/dev/null; then
    echo >&2 "Error: This script requires arch-install-scripts, please run:"
    echo >&2 "> pacman -S arch-install-scripts"
    exit 1
fi

# This script creates a filesystem as root
this_script_must_be_run_as_root

# Get command line args
if [ ! -d $1 ]; then
    echo >&2 "Error: '$root_dir': no such directory"
    exit 1
fi

# Argument parsing
root_dir="$(readlink --canonicalize $1)"
hostname="$2"
root_password_file="$3"

if [ ! -r $root_password_file ]; then
    echo >&2 "Error: password file '$root_password_file' must be readable"
    exit 1
fi

# Initialize /etc/machine-id at something different than the machine-id of the host
echo_status "Initializing machine-id"
systemd-machine-id-setup --root="$root_dir" --print

# The actual Arch Linux setup starts here
echo_status "Installing base Arch Linux"
if test -e /etc/arch-release; then
  pacstrap -c -d "$root_dir" base
else
  (
    cd /tmp
    wget --continue $ARCH_MIRROR/iso/$ARCH_RELEASE_DATE/archlinux-bootstrap-$ARCH_RELEASE_DATE-x86_64.tar.gz
    tar --strip-components=1 --directory="$root_dir" -xf archlinux-bootstrap-$ARCH_RELEASE_DATE-x86_64.tar.gz
    curl "$MIRRORLIST_URL" | sed 's/^#//' > "$root_dir"/etc/pacman.d/mirrorlist
  )

  systemd-nspawn --quiet --directory "$root_dir" --bind /dev/urandom:/dev/random /usr/bin/pacman-key --init
  systemd-nspawn --quiet --directory "$root_dir" /usr/bin/pacman-key --populate archlinux
fi

systemd-nspawn -D "$root_dir" /usr/bin/pacman -Syu --needed --noconfirm base vim openssh rxvt-unicode-terminfo

echo_status "Configuring base system"
echo_status "Setting timezone to $SADM_TIMEZONE"
ln -sf "/usr/share/zoneinfo/$SADM_TIMEZONE" "$root_dir/etc/localtime"

if [[ -n $hostname ]]; then
  echo_status "Setting hostname to $hostname"
  echo "$hostname" > "$root_dir/etc/hostname"
else
  echo_status "Not setting hostname: static configuration from kernel cmdline used"
fi

echo_status "Configuring locale to $SADM_LOCALE $SADM_CHARSET"
echo "LANG=$SADM_LOCALE" > "$root_dir/etc/locale.conf"
echo "$SADM_LOCALE $SADM_CHARSET" >> "$root_dir/etc/locale.gen"
# There is not `locale-gen --root`, we have to use a chroot
# systemd-nspawn isn't suitable because it overrides /etc/localtime
arch-chroot "$root_dir" /usr/bin/locale-gen

echo_status "Setting root password"
root_password=$(cat $root_password_file)
if [[ -n $root_password ]]; then
  echo "root:$root_password" | chpasswd --root "$root_dir"
else
  echo_status "Warning: root password file empty, not setting any root password"
fi

echo_status "Disabling pam_securetty, see https://github.com/systemd/systemd/issues/852#issuecomment-127759667"
sed -i '/pam_securetty.so/s/^/#/' $root_dir/etc/pam.d/login

echo_status "Setting up NTP"
# TOOD(halfr): move this to a dedicated conf file in the repo
echo "[Time]
NTP=ntp.prolo" > "$root_dir/etc/systemd/timesyncd.conf"

echo_status "Configuring DHCP for all en* interfaces"
# TOOD(halfr): move this to a dedicated conf file in the repo
echo "[Match]
Name=eth* en* host*

[Network]
DHCP=yes
LLDP=yes
EmitLLDP=customer-bridge" > "$root_dir/etc/systemd/network/50-dhcp.network"

echo_status "Copying resolv.conf"
if [[ $hostname == gw.prolo ]]; then
  resolvconf_file=../etc/resolv.conf.gw
else
  resolvconf_file=../etc/resolv.conf.servers_users
fi
cp -v $resolvconf_file "$root_dir/etc/resolv.conf"

echo_status "Enabling base services"
systemctl --root "$root_dir" enable sshd systemd-timesyncd systemd-networkd

echo_status "Basic Arch Linux setup done!"
