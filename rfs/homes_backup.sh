#!/bin/bash

set -e
set -x

if [ $# -le 2 ]; then
    >&2 echo "Missing parameter. Usage:"
    >&2 echo "$(basename $0) output_directory nbd_files"
    >&2 echo ""
    >&2 echo -e \
        " Generates tarballs of every home nbd in the current directory,\n" \
        "and places them in the given directory. You'll have to execute this\n" \
        "script on each rhfs:/export/hfs*, then rsync the files to a single\n" \
        "server. The files can then be exported directly to\n" \
        "prologin@rosa:~/homes/[year]/. Check for absurdly heavy tarballs."
    exit 1
fi

output_directory="$1"
shift
exclude_list="$(dirname "$(realpath "$0")")"/homes_backup_exclude_patterns

root_mnt="$1"
mkdir -p "${root_mnt}"
shift

for user_nbd in "$@"; do
    user="$(basename "$(echo $user_nbd | cut -d . -f 1)")"
    mount_dir="${root_mnt}/${user}"
    umount "${mount_dir}" || :
    echo "backing up $user"
    fsck.ext4 -r -y "$user_nbd" || {
        if [ $? -ge 4 ]; then
            echo "> fsck failed for $user. **SKIPPING**"
            exit 1
        fi
    }

    site_id=$(/opt/prologin/venv/bin/python -c \
	      "print(__import__('prologin.udb.client').udb.client.connect().query(login='$user', group='user')[0]['id'])" || :)
    output_file="${output_directory}/${site_id}.tar.gz"
    workdir="${output_directory}/${user}"

    if [ -z "$site_id" ] ; then
        echo ">> Failed to resolve site id for $user, **SKIPPING**"
        continue
    fi

    mkdir -p "$mount_dir" "$workdir"
    mount -o ro "$user_nbd" "$mount_dir"
    rsync -azh --exclude-from="${exclude_list}" "$mount_dir"/ "$workdir"/
    find "$workdir" -xdev -type f -size +10M -delete
    tar czf "${output_directory}/${site_id}.tar.gz" \
        -C "${workdir}/.." \
        "$user"

    umount "$mount_dir"
    echo "Exported $user"
done
