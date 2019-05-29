#! /bin/bash

echo "maintainer (Name <email>) :"

read MAINTAINER
if [ -z "$MAINTAINER" ]
then
  echo "maintainer name should not be empty"
  exit 126
fi

echo "extension marketplace id: "

read EXTENSION

if [ -z "$EXTENSION" ]
then
  echo "extension should not be empty"
  exit 127
fi

echo "extension package name: "

read PKGNAME

if [ -z "$PKGNAME" ]
then
  echo "extension pkgname should not be empty"
  exit 128
fi



mkdir "vscode-$PKGNAME"

cp PKGBUILD.vscode-plugin-template "./vscode-$PKGNAME/PKGBUILD"

sed -i "s/%COOLNAME%/$PKGNAME/g" "./vscode-$PKGNAME/PKGBUILD"
sed -i "s/%EXTENSION%/$EXTENSION/g" "./vscode-$PKGNAME/PKGBUILD"
sed -i "s/%MAINTAINER/$MAINTAINER/g" "./vscode-$PKGBUILD/PKGBUILD"
