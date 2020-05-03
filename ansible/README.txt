This is a work-in-progress, the intent is to completely replace the sadm
install scripts and a large part of the container setup scripts.

HOWTO:

1. Follow https://prologin-sadm.readthedocs.io/containers.html until it asks
   you to run ./container_setup_host.sh. This will create an arch_linux_base
   image in /var/lib/machines that you will use to spawn new machines

2. Create a script to spawn new machines easily:

cat >/var/lib/machines/spawn_prolo_test_machine.sh <<EOF
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
EOF

Make sure to have /root/.ssh/id_*.pub == your public key, to be able to ssh to
the machines afterwards.


3. Spawn all the required machines

cd /var/lib/machines
./spawn_prolo_test_machine.sh mygw
./spawn_prolo_test_machine.sh mymonitoring
./spawn_prolo_test_machine.sh myweb
./spawn_prolo_test_machine.sh myrhfs01
./spawn_prolo_test_machine.sh mymisc


4. Run ansible

ansible-playbook playbook-sadm.yml
