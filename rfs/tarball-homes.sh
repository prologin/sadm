#!/bin/bash
# $1: destination directory

trap 'umount /mnt/usr_user_home;exit' INT KILL
mkdir -p /mnt/cur_user_home
for user_nbd in $(ls | grep .nbd | grep -v backup_); do 
  user=$(echo $user_nbd | cut -d . -f 1)
  fsck.ext4 -r -y $user_nbd &> /dev/null
  rc_fsck=$?
  if [ "$rc_fsck" -ge 4 ]; then
    echo "[FAIL] ERROR: fsck failed with $rc_fsck for $user. **SKIPPING**"
    continue
  fi
  site_id=$(/var/prologin/venv/bin/python -c \
	  "print(__import__('prologin.udb.client').udb.client.connect().query(login='$user', group='user')[0]['id'])" \
	  2>/dev/null)
  if [ -z "$site_id" ] ; then
    echo "[FAIL] Failed to resolve site id for $user, **SKIPPING**"
    continue
  fi

  mount $user_nbd /mnt/cur_user_home
  find /mnt/cur_user_home -name 'vgcore.*' -delete
  rm -rf /mnt/cur_user_home/{.cache,.local,workspace,.config,0ad,.atom,.mozilla,.teeworlds,.q3a,.ICEauthority,.xsession-errors*,.armagetronad,.eclipse,.PyCharm*,.openttd}
  big_files=$(find /mnt/cur_user_home -xdev -type f -size +10M)
  if [[ $(echo $big_files) != "" ]]; then
    echo 'These big files were found :'
    echo "$big_files"
    echo 'Would you like to delete them ? y/n'
    read answer
    if [[ "$answer" == "y" ]]; then
      echo $big_files | xargs rm -rf
    fi
  fi
  tar czf $1/$site_id.tar.gz -C /mnt/cur_user_home .
  umount /mnt/cur_user_home

  echo "[OK] Exported $user"
done

