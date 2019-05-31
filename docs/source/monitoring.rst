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

1. ``bootstrap_arch_linux.sh``
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

Grafana configuration
---------------------

In a nutshell:

1. Install the ``grafana`` package.
2. Copy the SADM configuration file: ``etc/grafana/grafana.ini``.
3. Enable and start the ``grafana`` service
4. Copy the nginx configuration: ``etc/nginx/services/grafana.nginx``
5. Open http://grafana/, login and import the SADM dashboards from
   ``etc/grafana``.

.. todo:: automate the process above

Monitoring screen how-to
------------------------

Start multiple ``chromium --app http://grafana/`` to open a monitoring web
view.

We look at both the ``System`` and ``Masternode`` dashboards from grafana.

Disable the screen saver and DPMS using on the monitoring display using::

  $ xset -dpms
  $ xset s off

Log monitoring
--------------

On monitoring::

  $ pacman -S elasticsearch kibana
  $ systemctl enable --now elasticsearch kibana

In the kibana web UI, go to the dev tools tab and run::

  # Make sure the index isn't there
  DELETE /logs

  # Create the index
  PUT /logs

  PUT logs/_mapping
  {
    "properties": {
      "REALTIME_TIMESTAMP": {
        "type": "date",
        "format": "epoch_millis"
      }
    }
  }

It creates an index called logs, as well as proper metadata for time filtering.

Install https://github.com/multun/journal-upload-aggregator on the monitoring
server, and *please do not* configure nginx as a front-end on ``journal-aggregator``.
Don't forget
to add the alias in ``mdb``.

On the machines that need to be monitored, create ``/etc/systemd/journal-upload.conf``::

  [Upload]
  Url=http://journal-aggregator:20200/gateway

If still not fixed, also create ``/etc/systemd/system/systemd-journal-upload.service.d/restart.conf``: ::

  [Service]
  Restart=on-failure
  RestartSec=4

Then::

  $ systemctl enable --now systemd-journal-upload
