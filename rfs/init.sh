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

pacman -Sy devtools nfs-utils sshd
mkdir -p "$ROOTFS"
for svc in {sshd,nfsd,rpc-{idmapd,gssd,mountd,statd}}.service; do
  systemctl enable "$svc"
  systemctl start  "$svc"
done
echo "$ROOTFS $SUBNET(ro,no_root_squash,subtree_check,async)" > /etc/exports.d/rootfs.exports
exportfs -arv
mkarchroot "$ROOTFS" base $PACKAGES
cp -rv initcpio $ROOTFS/lib/
mkarchroot -r "rfs.sh" "$ROOTFS"
