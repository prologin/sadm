Monitoring
==========

Monitoring is the art of knowning when something fails, and getting as much
information as possible to solve the issue.

We will use a separate machine for monitoring, install it with the same base
Arch Linux configuration as the other servers.

We will use `prometheus <http://prometheus.io/>`_ as our monitoring backend and
`grafana <https://grafana.com/>`_ for the dashboards.

Setup
-----

To make a good monitoring system, mix the following ingredients, in that order:

1. ``boostrap_arch_linux.sh``
2. ``setup_monitoring.sh``
3. ``python install.py prometheus``
4. ``systemctl enable --now prometheus``
5. ``python install.py grafana``
6. ``systemctl enable --now grafana``

Monitoring services
-------------------

Most services come with built-in monitoring and should be monitored as soon
as prometheus is started.

The following endpoints are availables:

- ``http://udb/metrics``
- ``http://mdb/metrics``
- ``http://concours/metrics``
- ``http://masternode:9021``
- ``http://presencesync:9030``
- hfs: each hfs exports its metrics on ``http://hfsx:9030``
- workernode: each workernode exports its metrics on ``http://MACHINE:9020``.
