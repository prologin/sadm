CDROM=archlinux-2018.05.01-x86_64.iso

virt-install --connect qemu:///system                  \
  --name gw.prolo                                      \
  --memory 2048                                        \
  --vcpus=2,maxvcpus=4                                 \
  --cpu host                                           \
  --cdrom "$CDROM"				       \
  --disk size=40                                       \
  --disk size=40                                       \
  --network network=default                            \
  --network bridge=br-prolo                            \
  --virt-type kvm                                      \
  --graphics spice                                     \
  --os-variant centos7.0
