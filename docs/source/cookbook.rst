Cookbook
========

All the things you might need to do as an organizer or a root are documented
here.

Server setup
------------

Here is a list of things to remember when setting up servers:

- Use ssh as soon as possible.
- Work in a tmux session, this allows any other root to take over your work if
  needed.
- Use only one user and one shell (bash) and setup an infinite history. This,
  http://stackoverflow.com/a/19533853 is already installed by the rfs scripts.
  Doing that will document what you and the other admins are doing during the
  contest.

Testing on qemu/libvirt
-----------------------

Here are some notes:

- Do not use the spice graphical console for setting up servers, use the serial
  line. For syslinux it is ``serial 0`` at the top of ``syslinux.cfg`` and for
  Linux ``console=ttyS0`` on the cmd line of the kernel in ``syslinux.cfg``.
- For best performance use the VirtIO devices (disk, NIC), this should already
  be configured if you used ``virt-install`` to create the machine.
- For user machines, use the QXL driver for best performance with SPICE.

User related operations
-----------------------

Most of the operations are made very simple with the use of ``udb``. If you are
an organizer, you can access ``udb`` in read only mode. If you are a root, you
obviously have write access too.

``udb`` displays the information (including passwords) of every contestant to
organizers. Organizers can't see the information of other organizers or roots.

All services should be using ``udb`` for authentication. Synchronization might
take up to 5 minutes (usually only one minute) if anything is changed.

Giving back his password to a contestant
    First of all, make sure to ask the contestant for his badge, which he
    should always have on him. Use the name from the badge to look up the user
    in the ``udb``. The password should be visible there.

Adding an organizer
    **Root only**. Go to ``udb`` and add a user with type ``orga``.

Send an announce
    Connect to the IRC server, join the #notify channel, and send a message
    formatted like this::

      !announce <expiration-delay> <message>

    Example::

      !announce 12 The lunch is ready!

    Will create an announce which will stay for 12 minutes on the users's
    desktops. Note that the delay will default to 2 when not specified::

      !announce No milk today :(

Machine registration
--------------------

``mdb`` contains the information of all machines on the contest LANs. If a
machine is not in ``mdb``, it is considered an alien and won't be able to
access the network.

All of these operations are **root only**. Organizers can't access the ``mdb``
administration interface.

Adding a user machine to the network
    In the ``mdb`` configuration, authorize self registration by adding a
    VolatileSetting ``allow_self_registration`` to true. Netboot the user
    machine - it should ask for registration details. After the details have
    been entered, the machine should reboot to the user environment. Disable
    ``allow_self_registration`` when you're done.

Adding a machine we don't manage to the user network
    Some organizers may want to use their laptop. Ask them for their MAC
    address and the hostname they want.
    Finally, insert a ``mdb`` machine record with machine type ``orga`` using
    the IP address you manually allocated (if you set the last allocation to
    100, you should assign the IP .100). Wait a minute for the DHCP
    configuration to be synced, and connect the laptop to the network.

Network FS related operations
-----------------------------

Two kind of network file systems are used during the finals, the first one is
the Root File System: RFS, the second is the Home File System: HFS.  The current
setup is that a server is both a RFS and a HFS node.

The RFS is a read-only NFS mounted as a rootnfs in Linux. It is replicated over
multiple servers to ensure minimum latency over the network.

The HFS is a read-write,
exclusive, user-specific export of their home. In other words, each user has
it's own personal space that can only be mounted once at a time. The HFS exports
are sharded over multiple servers.

Resetting the hfs
~~~~~~~~~~~~~~~~~

If you need to delete every ``/home`` created by the hfs, simply delete all nbd
files in ``/export/hfs/`` on all HFS servers and delete entries in the
``user_location`` table of the hfs' database::

  # For each hfs instance
  rm /export/hfs/*.nbd

  echo 'delete from user_location;' | su - postgres -c 'psql hfs'

