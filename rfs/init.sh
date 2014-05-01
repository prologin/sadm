#!/bin/bash

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

# Install the tools needed to install and serve the rfs
pacman -Sy --needed --noconfirm arch-install-scripts nfs-utils openssh

# Enable and start the services need to serve the rfs
for svc in {sshd,nfsd,rpc-{idmapd,gssd,mountd,statd}}.service; do
  systemctl enable "$svc"
  systemctl start  "$svc"
done

# Install the base system (in rfs)
pacstrap -d "$ROOTFS" base $PACKAGES

# Copy some tools we will use in chroot
cp -rv initcpio $ROOTFS/lib/    # initramfs hook
cp -rv .. "$ROOTFS/sadm"        # sadm (we'll need some of it's services)
cp rfs.sh "$ROOTFS/"            # the script executed by chroot below

# Chroot to continue work
arch-chroot "$ROOTFS" bash /rfs.sh

# Clean the rfs by removing our installation tools
rm -f "$ROOTFS/rfs.sh"
rm -rf "$ROOTFS/sadm"

# And finally export the rfs via nfs
echo "$ROOTFS $SUBNET(ro,no_root_squash,subtree_check,async)" > /etc/exports.d/rootfs.exports
exportfs -arv
echo "--------------"
echo "WARNING: Do not forget to copy the initrd and the kernel ($ROOTFS/boot/initramfs-linux.img and $ROOTFS/boot/vmlinuz-linux) to the directory specified in ./etc/prologin/netboot.yml (likely /srv/tftp/) and name them respectively 'initrd' and 'kernel'"
echo "--------------"
