#!/bin/bash


SADM_FGP=F4592F5F00D9EA8279AE25190312438E8809C743
WORKDIR=repo.prologin.org

PKG_PATH=${1?Usage: $0 package.pkg.tar.xz}
PKG=$(basename $PKG_PATH)

set -e

echo "[+] System checks"

test -e /etc/arch-release || (echo >&2 'This is script should be run on Arch Linux'; exit 1)
which >/dev/null gpg || (echo >&2 'Please install gnupg'; exit 1)
which >/dev/null rsync || (echo >&2 'Please install rsync'; exit 1)

echo "[+] Checking gpg key store"

if ! gpg --list-secret-keys $SADM_FGP >/dev/null 2>&1; then
    cat >&2 <<EOF
The GPG key store is missing the prologin private key.

To get it, run:

    $ ssh repo@prologin.org 'gpg --export-secret-keys --armor $SADM_FGP' | gpg --import
EOF
    exit 1
fi

mkdir -p $WORKDIR
echo "[+] Copying and signing the package"
cp -v $PKG_PATH $WORKDIR/$PKG
gpg --sign --local-user $SADM_FGP --detach-sign --output $WORKDIR/$PKG.sig $WORKDIR/$PKG
echo "[+] Retrieving the database"
rsync -Pha repo@prologin.org:www/{prologin.db,prologin.db.sig,prologin.db.tar.gz,prologin.db.tar.gz.sig,prologin.pub} $WORKDIR/
echo "[+] Adding the package to the database"
repo-add --sign --verify --key $SADM_FGP $WORKDIR/prologin.db.tar.gz $WORKDIR/$PKG
echo "[+] Uploading the package and the database"
rsync -Pha $WORKDIR/$PKG{,.sig} $WORKDIR/prologin.{db,db.sig,db.tar.gz,db.tar.gz.sig,pub} repo@prologin.org:www/
