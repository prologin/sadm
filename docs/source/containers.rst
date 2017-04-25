Container setup for SADM
========================

This page explains how to run and test the Prologin SADM infrastruction using
containers.

.. note::

  TL;DR run ``container_setup_gw.sh`` from ``install_scripts/``

Why containers?
---------------

Containers are lightweight isolation mechanisms. You can think of them as
"starting a new userland on the same kernel", contrarily to virtual machines,
where you "start a whole new system". You may know them from tools such as
`docker <https://www.docker.com>`_, `kubernetes <https://kubernetes.io>`_ or
`rkt <https://github.com/coreos/rkt>`_. In this guide we will use
`system-nspawn(1)
<https://www.freedesktop.org/software/systemd/man/systemd-nspawn.html>`_, which
you already have installed if you are using systemd. Its main advantages
compared to other container managers are:

- Its simplicity. It does one thing well: configuring namespaces, the core of
  containers. No configuration file, daemon (other than systemd), managed
  filesystem or hidden network configuration. Everything is on the command line
  and all the options are in the man page.
- Its integrated with the systemd ecosystem. A container started with
  ``systemd-nspawn`` is registered and managable with `machinectl(1)
  <https://www.freedesktop.org/software/systemd/man/machinectl.html>`. You can
  use the ``-M`` of many systemd utilities to control it.
- Its feature set. You can configure the filesystem mapping, network interfaces,
  resources limits and security properties you want. Just look at the man page
  to see the options.

Containers compare favorably to virtual machines on the following points:

- Startup speed. The containers share the devices of the host, these are
  already initialised and running therefore the boot time is reduced.
- Memory and CPU resources usage. No hypervisor and extra kernel overhead.
- Storage. The content of the container is stored in your existing file system
  and is actually completely editable from outside of the container. It's very
  useful for inspecting what's going on.
- Configuration. For `system-nspawn`, the only configuration you'll have is the
  command line.

Overview
--------

This guides starts by discussing the virtual network setup, then we build and
start the systems.

Virtual network setup
---------------------

The first step consists in creating a virtual network. Doing it with containers
is not that different compared to using virtual machines. We can still use
bridge type interfaces to wire all the systems together, but we also have new
possibilities, as the container is running on the same kernel as the host
system.

One interesting thing is that we will be able to start one system as a
container, let say gw.prolo, and others as virtual machines, for example the
contestant systems, to test network boot for example.

We will use a bridge interface, the next problem to solve is to give this
interface an uplink: a way to forward packets to the internet, and back again.
To do that, we have multiple choices, here are two:

- Masquerade ("NAT") the ``vz-prolo`` bridge type interface behind your uplink.
  With this technique the packets arriving on ``vz-prolo`` will be rewritten,
  tracked and moved to your uplink to be routed as if they originated from it.
  The machines behind the NAT will not be accessible directly and you will have
  to setup port forwarding to access them from outside your system. From within
  your system they will be accessible directly using their local IP address. In
  this guide we will use the "zone" network type of ``systemd-nspawn`` and
  ``systemd-networkd`` as the main system network manager. ``systemd-networkd``
  will manage the NAT in iptables for us. Be careful, if you shadowed the
  ``80-container-vz.network`` rule with a catch-all (``Name=*``) ``.network``
  configuration files, the NAT will not be created.
- Bridge your uplink interface with ``vz-prolo``. This will have the bad effect
  to link your LAN, which is most likely already using your router DHCP server,
  to SADM network, which has its own DHCP server. Depending on various
  parameters your machine and those on your LAN might get IPs and DNS
  configuration from Prologin SADM. Be careful if you choose this option, as
  bridging your uplink will down the interface, ``vz-prolo`` will get an IP
  from your DHCP server if you use one and you may have to clean your routes to
  remove the old ones. It is still the fastest to setup, especially if you just
  want to give internet to a container. Note: some wireless drivers such as
  broadcom's ``wl`` do not support bridging 802.11 interfaces.

The NAT setup is simpler and more flexible, that's what we will use.

All the containers will be connected to their own L2 network using a bridge
interface. This interface is managed by systemd, created when the first
container using it is spawned.  Here is a small diagram to explain how we want
the network to look like::


       /---------\
       |   WAN   |
       \---------/
            |
            | < NAT
            |
     +----------------------------------------------------+
     |                 bridge: vz-prolo                   |
     +-+===========+----+============+------+===========+-+
       | if: vb-gw |    | if: vb-web |      | if: vnet0 |
       +-----------+    +------------+      +-----------+
           |                 |                   |
           | < veth          | < veth            | < VM interface
           |                 |                   |
       +-------+         +-------+           +------+
       | host0 |         | host0 |           | ens3 |
    o--+=======+----o o--+=======+-----o  o--+======+--o
    | container: gw | | container: web |  | VM: r00p01 |
    o---------------o o----------------o  o------------o

Veth type interfaces what we will use) linked to a bridge will have the name
``host0``. ``systemd-networkd`` provides a default configuration
(``80-container-host0.network``) file that enable DHCP on them. With the NAT
rule managed by ``systemd-networkd`` and that, the internet will be accessible
out-of-the-box in the conatiners. The only remaining configuration to do being
the DNS resolver (``/etc/resolv.conf``).

Setting up gw
-------------

Let's boot the first container: ``gw``

Everything starts with an empty directory. This is where we will instantiate the
file system used by ``gw``::

  $ mkdir gw

Use the Arch Linux install script from the sadm repository to populate it. Here
is how to use it::

  # ./install_scripts/bootstrap_arch_linux.sh /path/to/container machine_name ./file_containing_plaintest_root_pass

We suggest storing the password in a text file. It's a good way to be able to
to reproduce the setup quickly. If you don't want that, just create the file on
the fly or delete it afterwards.

The first system we build is `gw`, so let's create the container accordingly.
Run it as root::

  # ./install_scripts/bootstrap_arch_linux.sh /path/to/gw gw ./plaintest_root_pass

Packages will get installed a few scripts run to configure the Arch Linux system.
This is the same script we use for the bare metal or VM setup.

Then, start the container with a virtual ethernet interface connected to the
``vz-prolo`` network zone, a bridge interface managed by systemd, as well an
ipvlan interface linked to your uplink::

  # systemd-nspawn --boot --directory /path/to/gw --network-zone=prologin

.. note::

  To exit the container, press 'ctrl+]' three time. ``systemd-nspawn`` told you
  that when it started, but there is good chance you missed it, so we are
  putting it here just for you :)

You should see systemd booting, all the units should be ``OK`` except ``Create
Volatile Files and Directories.`` which fails because ``/sys/`` is mounted
read-only by ``systemd-nspawn``. After the startup you should get a login
prompt. Login as `root` and check that you see the virtual interface named ``host0`` in
the container using ``ip link``::

    # ip link
    1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1
        link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    2: host0@if3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default qlen 1000
        link/ether e6:28:86:d2:de:6e brd ff:ff:ff:ff:ff:ff link-netnsid 0

The host system should have two new interfaces:

- ``vz-prolo``, a bridge type interface.
- ``vb-gw``, a veth device whose master is ``vz-prolo``, meaning it's wired in
  this bridge.

Both these interface have an extra ``@...`` suffix. It is not part of the
interface name and simply indicates their peer interface.

If you are running ``systemd-networkd`` on your host system, with the default
configuration files, the ``vz-prolo`` interface will get an IP from a private
subnet and a ``MASQUERADE`` rule will be inserted into iptables. You can start
``systemd-networkd`` inside the container to get an IP in the ``vz-prologin``
network, which will be NAT'ed to your uplink.

For some reason ``host0`` cannot be renamed to ``prologin`` by a
``systemd-networkd`` .link file. What needs to be changed to account for that
is:

- The firewall configuration

You can do the usual install, with the following changes:

- In ``prologin.network``, in ``[Match]``, set ``Name=host0`` to match the
  virtualized interface.

What will *not* work:

- Some services are disabled when run in a container, for example
  ``systemd-timesyncd.service``.
- ``nic-configuration@host0.service`` will fail (``Cannot get device pause
  settings: Operation not supported``) as this is a virtual interface.

.. note::

    When you exit the container everything you started inside it is killed. If
    you want a persistent container, run::

      # systemd-run systemd-nspawn --keep-unit --boot --directory /full/path/to/gw --network-zone=prologin
      Running as unit run-r10cb0f7202be483b88ea75f6d3686ff6.service.

    And then monitor it using the transient unit name::

      # systemctl status run-r10cb0f7202be483b88ea75f6d3686ff6.service

Manual network configuration
----------------------------

This section is a do-it-yourself version of the ``--network-veth
--network-bridge=prologin`` nspawn's arguments. The main advantage of doing so
is that the interfaces are not deleted when the container is shut down. Its
useful if you have iptables rules you want to keep.

First let's make sure we have ip forwarding enabled, without that the bridge
will move packets around::

  # echo 1 > /proc/sys/net/ipv4/ip_forward

We will create a bridge interface named ``prologin`` that will represent the
isolated L2 network for SADM::

  # ip link add prologin type bridge

You can now see the prologin interface using::

  # ip link show
  ...
  4: prologin: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default qlen 1000


For each system we want to start, we create a `veth <http://blog.scottlowe.org/2013/09/04/introducing-linux-network-namespaces/>`_ and plug one end to the
bridge. For example for the ``gw``::

  # ip link add gw.local type veth peer name gw.bridge
  # ip link show label 'gw*'

Here we create the two virtual ethernet interfaces, ``gw.local@gw.local`` and
``gw.bridge@@gw.bridge``. On veth pairs, a packet arriving to one these
interface is dispatched to the other. When manipulating them only the part of
the name before the ``@`` is required, the other is just a reminder of what
interface is at the other end.

Let's wire ``gw.bridge`` to the bridge::

  # ip link set gw.bridge master prologin

You can see that the interface is connected to the bridge with the ``master
prologin`` keyword on the following command::

  $ ip link show gw.bridge

The interface is not running (``state DOWN``), we have to enable it::

  # ip link set dev prologin up

Going further/discussion
========================

What could make your container usage better?

- Use the ``--overlay`` option from ``systemd-nspawn``. Have only one base Arch
  Linux distro and build other systems form it. It reduces the time to install
  and disk usage (if that's your concern).
