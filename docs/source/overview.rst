Infrastructure overview
=======================

This section describes what runs on our servers and what it is used for.

Needs
-----

- Host 100 contest participants + 20 organizers on diskless computers connected
  to a strangely wired network (2 rooms with low bandwidth between the two).
- Run several internal services:
    - DHCP + DNS
    - Machine DataBase (MDB)
    - User DataBase (UDB)
    - NTPd
- Run several external services (all of these are described later):
    - File storage
    - Homepage server
    - Wiki
    - Contest website
    - Bug tracking software (Redmine)
    - Documentation pages
    - IRC server
    - Minecraft server
    - Pastebin
    - Matches cluster

Network infrastructure
----------------------

We basically have two local networks:

- User LAN, containing every user machine (Pasteur + IP12A) and all servers.
- Matches LAN, containing the cluster master and all the cluster slaves.

The User LAN uses 192.168.0.0/24, and the gateway (named ``gw``) is
192.168.1.254. 192.168.1.0/24 is reserved for servers, and 192.168.250.0/24
is reserved for machines not in the MDB.

The Matches LAN uses 192.168.2.0/24, and the gateway (named ``gw.cl``) is
192.168.2.254.

Both ``gw`` and ``gw.cl`` communicate through an OpenVPN point to point
connection.

Machine database
----------------

The Machine DataBase (MDB) is one of the most important part of the
architecture. Its goal is to track the state of all the machines on the network
and provide information about the machines to anyone who needs it. It is
running on ``mdb`` and exports a web interface for administration (accessible
to all roots).

A Python client is available for scripts that need to query it, as well as a
very simple HTTP interface for use in PXE scripts.

It stores the following information for each machine:

- Main hostname
- Alias hostnames (mostly for services that have several DNS names)
- IP
- MAC
- Nearest root NFS server
- Nearest home NFS server
- Machine type (user, orga, cluster, service)
- Room id (pasteur, alt, cluster, other)

It is the main data source for DHCP, DNS, monitoring and other stuff.

When a machine boots, an IPXE script will lookup the machine info from the MDB
(to get the hostname and the nearest NFS root). If it is not present, it will
ask for information on stdin and register the machine in the MDB.

User database
-------------

The User DataBase (UDB) stores the user information. As with MDB, it provides a
simple Python client library as well as a web interface (accessible to all
organizers, not only roots). It is running on ``udb``.

It stores the following information for every user:

- Login
- First name
- Last name
- Current machine name
- Password (unencrypted so organizers can give it back to people who lose it)
- At his computer right now (timestamp of last activity)
- Type (contestant, organizer, root)
- SSH key (mostly useful for roots)

As with the MDB, the UDB is used as the main data source for several services:
every service accepting logins from users synchronizes the user data from the
UDB (contest website, bug tracker, minecraft server, ...). A ``pam_udb``
service is also used to handle login on user machines.

File storage
------------

4 classes of file storage, all using NFS over TCP (to handle network congestion
gracefully):

- Root filesystem for the user machines: 99% reads, writes only done by roots.
- Home directories filesystem: 50% reads, 50% writes, needs low latency
- Shared directory for users junk: best effort, does not need to be fast, if
  people complain, tell them off.
- Shared directory for champions/logs/maps/...: 35% reads, 65% writes, can't be
  sharded, needs high bandwidth and low latency

Root filesystem is manually replicated to several file servers after any change
by a sysadmin. Each machine using the root filesystem will interogate the MDB
at boot time (from an IPXE script) to know what file server to connect to.
These file servers are named ``rfs-1, rfs-2, ...``. One of these file servers
(usually ``rfs-1``) is aliased to ``rfs``. It is the one roots should connect
to in order to write to the exported filesystem. The other rfs servers have the
exported filesystem mounted as read-only, except when syncing.

Home directories are sharded to several file servers. Machines interogate the
MDB to know what home file server is the nearest. When a PAM session is opened,
a script interogates the UDB to know what file server the home directory is
hosted on. If it is not the correct one, it sends a sync query to the old file
server to copy the user data to the new file server. These file servers are
named ``hfs-1, hfs-2, ...``

The user shared directory is just one shared NFS mountpoint for everyone. It
does not have any hard performance requirement. If it really is too slow, it
can be sharded as well (users will see two shared mount points and will have to
choose which one to use). This file server is called ``shfs``.

The shared directory for matches runners is not exposed publicly and only
machines from the matches cluster can connect to it. It is a single NFS
mounpoint local to the rack containing the matches cluster. The server is
connected with 2Gbps to a switch, and each machine from the cluster is
connecter do the same switch with a 1Gbps link. This file server is running on
``fs.cl``, which is usually the same machine as ``gw.cl``.

DHCP and DNS
------------

The DHCP server for the user network runs on ``gw``. It is responsible for
handing out IPs to machines connecting to the network. The MAC<->IP mapping is
generated from MDB every minute. Machines that are not in the MDB are given an
IP from the 192.168.250.0/24 range.

The DHCP server for the cluster network runs on ``gw.cl``. The MAC<->IP mapping
is also generated from MDB, but this time the unknown range is 192.168.2.200
to 192.168.2.250.

The DNS server for the whole infrastructure runs on ``ns``, which is usually
the same machine as ``gw``. The hostname<->IP mapping is generated from MDB
every minute. There are also some static mappings for the unknown ranges:
192.168.250.x is mapped to ``alien-x`` and 192.168.2.200-250 is mapped to
``alien-x.cl``.

Matches cluster
---------------

The matches cluster contains several machines dedicated to running Stechec
matches. It is a separate physical architecture, in a separate building, on a
separate LAN. The two gateways, ``gw.cl`` and ``gw`` are connected through an
OpenVPN tunnel.

``master.cl`` runs the Stechec master node, which takes orders from the Stechec
website (running on ``contest``, on the main LAN). All nodes in the cluster are
connected to the master node.

To share data, all the nodes are connected to a local NFS share: ``fs.cl``.
Read the file storage overview for more information.

Minecraft server
----------------

Surprisingly, setting up a Minecraft server integrated with UDB is pretty
complicated. A replacement for the Minecraft authentication server will be
running on ``mineauth``, aka. ``session.minecraft.net``. This server will need
to have a valid SSL key for the hostname (so we need to deploy our own CA) and
we need to patch ``minecraft.jar`` because it contains some keys and
certificates that we will need to modify.

Other small services
--------------------

Here is a list of all the other small services we provide that don't really
warrant a long explanation:

- Homepage: runs on ``homepage``, provides the default web page displayed to
  contestants in their browser
- Wiki: runs on ``wiki``, UDB aware wiki for contestants
- Contest website: runs on ``contest``, contestants upload their code and
  launch matches there
- Bug tracker: ``bugs``, UDB aware Redmine
- Documentations: ``docs``, language and libraries docs, also rules, API and
  Stechec docs.
- IRC server: ``irc``, small UnrealIRCd without services, not UDB aware
- Paste: ``paste``, random pastebin service
