Prologin's 2014 setup
=====================

Authors:

- Marin Hannache
- Paul Hervot
- Pierre Bourdon
- Rémi Audebert

Overview
--------

We had 2 rooms:

- Pasteur, ~ 96 machines, 95% of them working
- Masters, ~ 42 machines, 90% of them working

We did not setup an alternate cluster because we had enough computing power
with all the i7.

Electrical setup
----------------

We asked an electrician to setup Masters for ~40 machines.

Hardware setup
--------------

All machines were of i7 generation.

We used the machines already in Pasteur.

We moved machines from SM14 into Masters, used screens, keyboards and mice from
the storage room of the Bocal. Some SM14 machines were used a server and
stored in Pasteur. Each machine we took from SM14 had to put back exactly at
the same location se labeled accordingly.

We bought 10 500Go disks, 2 for each RHFS in RAID 1. The EPITA ADM lent us 4
1To racks that we used for the other servers: gw, web, misc1 and misc2.

.. note::

    We bought the same brand for all the disks, it is *not* a good idea to do
    that. If a disk from the batch is faulty, then it is pretty certain that the
    other are too. We should have bought disks from different manufacturers.

Network setup
-------------

Pasteur
~~~~~~~

There were 7 switches in Pasteur and 4 boxes to hold them. Each switch's uplink
was wired directly back to The Bocal but they could not setup a proper VLAN so
they brought a 24 port gibabit switch, removed uplinks from every switch and
wired them to this one.

Masters
~~~~~~~

We borrowed a 48 port Gigabit switch (`HP Procurve 2848`_) from the LSE and
satreix lent us his little 16 port Gbit switch. 3/4 of the room was on the 48
port switch and 1/4 was on the other one.

.. _HP Procurve 284: http://h10010.www1.hp.com/wwpc/ca/en/sm/WF06b/12136296-12136298-12136298-12136298-12136316-12136322-29584733.html

The link between Pasteur and Masters was done by a custom cable setup by the
Bocal.

Wifi for organizers
~~~~~~~~~~~~~~~~~~~

We used a `TP-LINK 703n <http://wiki.openwrt.org/toh/tp-link/tl-wr703n>`_ and
bridged the WLAN and LAN.

MAC addresses for the organizers' machines were added to mdb with an IP on the
services range.

Services organization
---------------------

GW:

- bind
- dhcpd
- firewall
- mdb
- netboot
- udb
- postgresql database for hfs

Web:

- concours
- postgresql database for concours
- redmine
- map

misc1:

- minecraft
- collectd
- graphite
- dj_ango

RHFS:

- rhfs01 (pasteur)
- rhfs23 (pasteur)
- rhfs45 (pasteur)
- rhfs67 (masters)

The gate lock
-------------

There should be another article on the subject.

Issues encountered during the event
-----------------------------------

Bad network setup
~~~~~~~~~~~~~~~~~

We asked for the network to be setup such as all links were on the same VLAN
and no dhcp server. Our gateway were to route the packets to the Bocal's
gateway.

Instead, no VLAN was setup, all uplinks were disconnected and all the switches
were connected to another Gigabit switch. Because we wanted to have an uplink,
we had to add another nic to our gateway and connect it to another network,
then route the packets from one interface to another.

Some of the iptables rules we used are in the cookbook.

Switch failure
~~~~~~~~~~~~~~

4~6 hours after the beginning of the event a switch suddenly stopped forwarding
packets. After quick checks we diagnosed a hardware problem, and asked the
contestants to go to another spot in the machine room.

We rebooted the switch and disconnected every cable from it and started looking
for the one that was giving us trouble. At some point it started to work again,
and did not fail thereafter. The only cables we did not connect were the
uplink, the IP phone and a strange PoE camera.

Services misconfigurations
~~~~~~~~~~~~~~~~~~~~~~~~~~

- mdbDNS misconfiguration: a machine was inserted with a bad hostname (it
  contained a '``_``'), causing bind to fail reading the configuration file.

- mdb and DHCP misconfiguration: the MAC address of a machine is used as the
  primary key, modifying it is like creating another entry in the table. For
  mdb is added another machine with the same hostname but with another MAC
  address.

Fix: Remove the offending entry from the database.

Ethernet flow control
~~~~~~~~~~~~~~~~~~~~~

One RHFS was flooding the neighboors with pause packets, causing the NBD/NFS to
be really slow and make the machines freeze.

Fix: ``ethtool --pause autoneg off rx off rx off``

References:

- `Beware Ethernet flow control <http://virtualthreads.blogspot.fr/2006/02/beware-ethernet-flow-control.html>`_
- `Wikipedia: Ethernet flow control <http://en.wikipedia.org/wiki/Ethernet_flow_control>`_

Bad NTP server
~~~~~~~~~~~~~~

We did not edit ntp configuration on the rfs root so it was trying to contact
``0.pool.ntp.org`` instead of ``gw.prolo``.

Fix: pssh on all machines "ntpdate gw && find /home -print0 | xargs -0 touch"

Cookbook
--------

Here are the tools, techniques, and knowledge we used to setup and run
everything.

LLDP
~~~~

The switches broadcasted LLDP packets to every machines connected to them. It
contains, among other things, the name of the switch and the port to wich the
link is connected. We used those packets to know where each machine was
connected, and select the closest RHFS.

.. note::

    Not all the switches sent those packets.

Reloading LVM/RAID devices
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # If using LVM, remove logical volumes
    $ dmsetup remove /dev/mapper/<NAME>
    # Deactivate MD device
    $ mdadm --stop /dev/mdXXX
    # Scan for hotplugged/swapped disks
    $ for d in /sys/class/scsi_host/host*/scan; do echo '- - -' > $d; done
    # Rescan for RAID devices
    $ mdadm --assemble --scan

iptables and ipset
~~~~~~~~~~~~~~~~~~

We used `ipset <http://ipset.netfilter.org/>`_ to implement ip-based filtering.

Sample usage::

    $ ipset -! create allowed-internet-access bitmap:ip range 192.168.0.0/23
    $ ipset add allowed-internet-access 192.168.0.42
    $ ipset flush allowed-internet-access
    # Allow packets having src in the set
    $ iptables -A FORWARD -m set --match-set allowed-internet-access src -j ACCEPT

Sample rules::

    # Rewrite packets going out of interface lan
    $ iptables -t nat -A POSTROUTING -o lan -j MASQUERADE
    # Allow packets coming from 192.168.1.0/24 to go out
    $ iptables -A FORWARD -s 192.168.1.0/24 -j ACCEPT
    # Black list a set of IP to access port 80
    $ iptables -A INPUT -i lan -p tcp --destination-port 80 -m set --match-set allowed-internet-access src -j DROP
    # Allow packets in an already established connection
    $ iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

Eggdrop's latency fixes
~~~~~~~~~~~~~~~~~~~~~~~

By default eggdrop added fakelag to the motus modules, we removed it by
patching the binary at runtime.
