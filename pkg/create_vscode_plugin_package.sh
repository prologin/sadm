#! /bin/bash

if [ -z "$1" ]
then
  echo "usage ./create_vscode_plugin_package.sh <marketplace_extension_id> <pkgname> <maintainer>"
  exit 1
fi

if [ -z "$2" ]
then
  echo "usage ./create_vscode_plugin_package.sh <marketplace_extension_id> <pkgname> <maintainer>"
  exit 1
fi

if [ -z "$2" ]
then
  echo "usage ./create_vscode_plugin_package.sh <marketplace_extension_id> <pkgname> <maintainer>"
  exit 1
fi

mkdir "vscode-$2"

cp PKGBUILD.vscode-plugin-template "./vscode-$2/PKGBUILD"

sed -i "s/%PKGNAME%/$2/g" "./vscode-$2/PKGBUILD"
sed -i "s/%EXTENSION%/$1/g" "./vscode-$2/PKGBUILD"
sed -i "s/%MAINTAINER%/$3/g" "./vscode-$2/PKGBUILD"
