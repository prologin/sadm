Support scripts:

* `common.sh` - Functions used in multiple scripts

Arch Linux setup:

* `bootstrap_arch_linux.sh` - Arch Linux install and configuration

Hardware dependent setup (VM, live setup):

* `bootstrap_from_install_medium.sh` - curl-able RAID1 sadm install script
* `bootstrap_arch_linux_raid1.sh` - Combined disk setup and Arch Linux install
* `bootstrap_fs_raid1.sh` - Create partitions, mdadm, lvm
* `bootstrap_fs_raid1_post.sh` - Configure boot on RAID1
