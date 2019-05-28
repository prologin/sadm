#! /bin/bash

echo "extension marketplace id: "

read EXTENSION

if [ -z "$EXTENSION" ]
then
  echo "extension should not be empty"
  exit 127
fi

echo "extension coolname: "

read COOLNAME

if [ -z "$COOLNAME" ]
then
  echo "extension coolname should not be empty"
  exit 128
fi



mkdir "vscode-$COOLNAME"

cp PKGBUILD.vscode-plugin-template "./vscode-$COOLNAME/PKGBUILD"

sed -i "s/%COOLNAME%/$COOLNAME/g" "./vscode-$COOLNAME/PKGBUILD"
sed -i "s/%EXTENSION%/$EXTENSION/g" "./vscode-$COOLNAME/PKGBUILD"
