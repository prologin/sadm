NAME=pas-r00p01.prolo

virsh --connect qemu:///system destroy $NAME
virsh --connect qemu:///system undefine $NAME

virt-install --connect qemu:///system                  \
  --name $NAME					       \
  --memory 1024                                        \
  --vcpus=2,maxvcpus=4                                 \
  --cpu host                                           \
  --nodisks                                            \
  --network bridge=br-prolo,model=e1000                \
  --pxe                                                \
  --graphics spice                                     \
  --virt-type kvm                                      \
  --os-variant centos7.0
