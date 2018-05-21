#!/bin/bash
# $1: destination directory

if [ "$#" -le "1" ]; then
  >&2 echo "Missing parameter. Usage:"
  >&2 echo "$(basename $0) output_directory"
  >&2 echo ""
  >&2 echo -e \
    " Generates tarballs of every home nbd in the current directory,\n" \
    "and places them in the given directory. You'll have to execute this\n" \
    "script on each rhfs:/export/hfs*, then rsync the files to a single\n" \
    "server. The files can then be exported directly to\n" \
    "prologin@rosa:~/homes/[year]/. Check for absurdly heavy tarballs."
  exit 1
fi

INFO_OK="\033[1;32m[OK]\033[0;39m  "
INFO_FAIL="\033[1;31m[FAIL]\033[0;39m"

root_mnt=$(mktemp -d)
for user_nbd in $(ls | grep .nbd | grep -v backup_); do
  user=$(echo $user_nbd | cut -d . -f 1)
  fsck.ext4 -r -y $user_nbd &> /dev/null
  rc_fsck=$?
  if [ "$rc_fsck" -ge 4 ]; then
    echo "$INFO_FAIL ERROR: fsck failed with $rc_fsck for $user. **SKIPPING**"
    continue
  fi
  site_id=$(/var/prologin/venv/bin/python -c \
	  "print(__import__('prologin.udb.client').udb.client.connect().query(login='$user', group='user')[0]['id'])" \
	  2>/dev/null)
  if [ -z "$site_id" ] ; then
    echo "$INFO_FAIL Failed to resolve site id for $user, **SKIPPING**"
    continue
  fi

  mount_dir="${root_mnt}/${user}"
  mkdir -p "$mount_dir"
  mount $user_nbd "$mount_dir"
  find "$mount_dir" -name 'vgcore.*' -delete
  rm -rf "$mount_dir"/{.cache,.local,workspace,.config,0ad,.atom,.mozilla,.teeworlds,.q3a,.ICEauthority,.xsession-errors*,.armagetronad,.eclipse,.PyCharm*,.openttd}
  big_files=$(find "$mount_dir" -xdev -type f -size +10M)
  if [[ $(echo $big_files) != "" ]]; then
    echo 'These big files were found :'
    echo "$big_files"
    echo 'Would you like to delete them ? y/n'
    read answer
    if [[ "$answer" == "y" ]]; then
      echo $big_files | xargs rm -rf
    fi
  fi
  tar czf $1/$site_id.tar.gz -C "${mount_dir}/.." "$user"
  umount "$mount_dir"
  rmdir "$mount_dir"

  echo "$INFO_OK Exported $user"
done
rm -r "$root_mnt"
