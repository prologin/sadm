Prologin's 2019 setup
=====================

Overview
--------

We had 2 rooms:

- Paster, 96 machines
- Masters, 41 machines

Network setup
-------------

Pasteur
~~~~~~~

There were 5 48 ports switches in Pasteur and 4 boxes to hold them.

gw.prolo had 1 nic and was the network gateway.

Roots and organizers were on the last 2 rows.

Masters
~~~~~~~

There were 2 24 ports switches (lent by the bocal).
There two RHFS (67 & 89).
The room was separated into two parts, each connected to a switch
and a RHFS. (67 & 89). The switches were interconnected, and one was connected
to the bocal network. (to link Pasteur <-> Master).

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

No major issue this year.

RHFS sync breaks login
~~~~~~~~~~~~~~~~~~~~~~

The ``rfs/commit_staging.sh`` script overwrites ``/etc/passwd``, and during the
time the ``rsync`` is running, this file does not contain the ``udb`` users.
This prevented users from logging in and for logged in users tools that relied
on it failed. The ``/etc/passwd`` file is updated by the ``udbsync_passwd``
service, which is run after the ``rsync`` is finished.

Impact on contestants: medium

Remediation: See https://github.com/prologin/sadm/issues/169

High network usage, freeze and OOM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After starting a match ``concours``, the user landed on the match replay page
and a non-identified bug in the match replay stack (Godot web) made the the
contestants system freeze due to high network usage.  Symptoms where full
bandwidth usage of the NIC, >100MB/s and high CPU usage. We suspect that the
code entered a busy loop hammering the NFS client. This prevented us from
logging-in with ssh, but the prometheus-node-exporter still worked and we could
gather logs. We initially had no clue what was causing the freeze, due to a
lack of per-process monitoring, but inspection of the machines when they were
frozen shown consistent correlation with opening a replay page on concours.
Also, users that did not open such page did not experience the freeze.

Unfreezing the machine required either to a) reboot the machine, with risk of
lost data and FS corruption, or b) unplug the network cable for some seconds
and re-plug it, after that waiting ~30 seconds and the OOM killer would kill
the browser. Multiple contestants did reboot their machines when they froze,
without data loss.

Impact on contestants: high, ~10 freeze per hour

Detection: created a dashboard in grafana to identify systems with abnormaly
high network bandwidth usage

Remediation: fix web replay, limit network bandwidth to allow ssh

Packet drop on uplink
~~~~~~~~~~~~~~~~~~~~~

Organizers using ``gw.prolo`` as uplink saw packet drop that mainly impacted
DNS queries. Other part of the network stack were also unstable, but DNS
failures had the most impact, mainly on the radio service that was querying
external APIs.

Impact on contestants: no impact

Detection: general packet loss, "Server IP address could not be found" error in browsers

Remediation: added retry of network requests

Next year: prepare a secondary uplink in case the main one fails

Heat
~~~~

We did not have enough fans and the temperature in the rooms was very high.

Next year: ensure each row has a large fan, put drink cart in front of the
room.
