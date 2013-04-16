Setup instructions
==================

Setting up the whole infrastructure is pretty difficult because of several
circular dependencies in the infrastructure. This section should explain
everything needed to setup the whole infrastructure from scratch.

TODO!

Building the iPXE bootrom
-------------------------

The iPXE bootrom is an integral part of the boot chain for user machines. It is
loaded by the machine BIOS via PXE and is responsible for booting the Linux
kernel using the nearest RFS. It also handles registering the machine in the
MDB if needed.

iPXE is an external open source project, clone it first::

  git clone git://git.ipxe.org/ipxe.git

Then compile time settings need to be modified. Uncomment the following lines::

  // in config/general.h
  #define REBOOT_CMD

You can now build iPXE: go to ``src/`` and build the bootrom using our script
provided in ``prologin-sadm/netboot``::

  make bin/undionly.kpxe EMBED=/path/to/prologin-sadm/netboot/script.ipxe
