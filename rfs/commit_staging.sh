#!/bin/sh

set -e

if (( $# < 1 )); then
    echo "Usage: $0 rfs0 rfs1 ..."
    exit 1
fi

echo "######## Pushing the kernel and initrd to gw ########"

scp /export/nfsroot_staging/boot/vmlinuz-linux       gw:/srv/tftp/kernel
scp /export/nfsroot_staging/boot/initramfs-linux.img gw:/srv/tftp/initrd


for serv in "$@"; do
    echo "######## SYNCING $serv ########"
    rsync --delete -axPHAX /export/nfsroot_staging/ "$serv":/export/nfsroot_ro
    rsync --delete -axPHAX /export/skeleton/ "$serv":/export/skeleton

    echo "## restarting metadata services on $serv"
    ssh -T root@"$serv" <<EOF
systemctl restart rootssh-copy
EOF

done
