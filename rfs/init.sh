#!/bin/bash

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
pacman -Sy archlinux-install-scripts nfs-utils openssh
for svc in {sshd,nfsd,rpc-{idmapd,gssd,mountd,statd}}.service; do
  systemctl enable "$svc"
  systemctl start  "$svc"
done
pacstrap -d "$ROOTFS" base $PACKAGES
cp -rv initcpio $ROOTFS/lib/
cp rfs.sh "$ROOTFS/"
arch-chroot "$ROOTFS" bash /rfs.sh
rm -f "$ROOTFS/rfs.sh"
echo "$ROOTFS $SUBNET(ro,no_root_squash,subtree_check,async)" > /etc/exports.d/rootfs.exports
exportfs -arv
