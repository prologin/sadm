#!/bin/bash

# This script setups the exported rootfs

set -e

if [ x"$ROOTFS" == "x" ]; then
  echo "ROOTFS not specified... aborting"
  exit 1
fi
if [ x"$SUBNET" == "x" ]; then
  echo "SUBNET not specified... aborting"
  exit 1
fi
if [ x"$PACKAGES" == "x" ]; then
  echo "PACKAGES not specified... aborting"
  exit 1
fi

mkdir -p "$ROOTFS"

echo 'Install the tools needed to install and serve the rfs'
pacman -Sy --needed --noconfirm arch-install-scripts nfs-utils openssh dnsutils nbd

echo 'Install the base system (in rfs)'
pacstrap -d "$ROOTFS" base $PACKAGES

echo 'Copy some tools we will use in chroot'
cp -rv initcpio $ROOTFS/lib/    # initramfs hook
cp -rv .. "$ROOTFS/root/sadm"   # sadm (we'll need some of it's services)
cp rfs.sh "$ROOTFS/root"        # the script executed by chroot below

echo 'Chroot to install the Arch Linux used by contestants'
arch-chroot "$ROOTFS" bash /root/rfs.sh

echo 'Give the new system a static nameserver (the gateway)'
# This is done outside of the chroot because inside, /etc/resolv.conf is bind-mounted
echo 'domain prolo
nameserver 192.168.1.254' > /export/nfsroot/etc/resolv.conf

echo 'Enable and start the services need to serve the rfs'
python install.py udbsync_passwd udbsync_rfs
for svc in {sshd,udbsync_passwd{,_nfsroot},udbsync_rootssh,rpcbind,nfs-server}.service rootssh.path; do
  systemctl enable "$svc"
  systemctl start  "$svc"
done

echo 'And finally export the rfs via nfs'
echo "$ROOTFS $SUBNET(ro,no_root_squash,subtree_check,async)" > /etc/exports.d/rootfs.exports
exportfs -arv

echo "--------------"
echo "WARNING: Do not forget to copy the initrd and the kernel
($ROOTFS/boot/initramfs-linux.img and $ROOTFS/boot/vmlinuz-linux) to the
directory specified in ./etc/prologin/netboot.yml (likely /srv/tftp/) and name
them respectively 'initrd' and 'kernel'"
echo "--------------"
