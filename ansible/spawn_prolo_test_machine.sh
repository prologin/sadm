#!/bin/bash

set -e

cd /var/lib/machines

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <machine_name>"
fi

machine="my$1"
machine_hostname="$1"

rsync --partial --info=progress2 -ha arch_linux_base/ "$machine"
mkdir -p "$machine"/root/.ssh
cat $HOME/.ssh/id_*.pub | tee "$machine"/root/.ssh/authorized_keys "$machine"/root/.ssh/authorized_keys2
chown -R root:root "$machine"/root/.ssh
chmod 700 "$machine"/root/.ssh
chmod 600 "$machine"/root/.ssh/*
echo "$machine_hostname" > "$machine"/etc/hostname

cat >/etc/systemd/nspawn/"$machine".nspawn <<NSPAWN
[Network]
Zone=prolo

[Files]
# Allows cp-ing from container to container
PrivateUsersChown=false
NSPAWN

machinectl start "$machine"
