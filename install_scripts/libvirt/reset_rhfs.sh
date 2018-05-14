VIRSH="virsh -c qemu:///system"

RHFS=01

$VIRSH vol-delete /var/lib/libvirt/images/rhfs${RHFS}.prolo.qcow2
$VIRSH vol-delete /var/lib/libvirt/images/rhfs${RHFS}.prolo-1.qcow2
$VIRSH vol-create-as default rhfs${RHFS}.prolo.qcow2 40G --format qcow2
$VIRSH vol-create-as default rhfs${RHFS}.prolo-1.qcow2 40G --format qcow2
