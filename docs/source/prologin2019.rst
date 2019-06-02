Prologin's 2019 setup
=====================

Overview
--------

We had 2 rooms:

- Paster, 96 machines
- Masters, 42 machines

Network setup
-------------

Pasteur
~~~~~~~

There were 5 48 ports switches in Pasteur and 4 boxes to hold them.

gw.prolo had 1 nice and was the network gateway.

Roots and organizers were on the last 2 rows.

Masters
~~~~~~~

Wifi for organizers
~~~~~~~~~~~~~~~~~~~

We used a NETGEAT AC1200 to bridge the WLAN with the LAN.

MAC addresses for the organizers' machines were added to mdb with an IP on the
services range.

Services organization
---------------------

gw.prolo:

- bind
- dhcpd
- firewall
- mdb
- netboot
- postgresql database for hfs
- udb

web.prolo:

- concours
- masternode
- postgresql database for concours
- map

misc.prolo:

- redmine
- djraio
- irc_gatessh
- sddm-remote
- spotify
- wow (World of Warcraft)

monitoring.prolo:

- elasticsearch
- grafana
- kibana
- prometheus

RHFS:

- rhfs01 (pasteur)
- rhfs23 (pasteur)
- rhfs45 (pasteur)
- rhfs67 (masters)
- rhfs89 (masters)

Issues encountered during the event
-----------------------------------

High network usage, freeze and OOM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Packet drop on uplink
~~~~~~~~~~~~~~~~~~~~~

Heat
~~~~

We did not have enough fans and the temperature in the rooms was very high.
