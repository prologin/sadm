Monitoring
==========

Monitoring is the art of knowning when services fails, and getting as much
information as possible to solve the issue.

We will use a separate machine for monitoring, install it with the same base
Arch Linux configuration as the other servers.

We will use `prometheus <http://prometheus.io/>`_ as our monitoring backend and
`promdash <https://github.com/prometheus/promdash>`_ for the frontend.

Setup
-----

For fast deployment, we will use docker::

  pacman -S docker
  systemctl enable docker && systemctl start docker

First, install prometheus::

  docker run --name prometheus --publish 9090:9090 --volume /root/sadm/etc/prometheus/:/prometheus-data prom/prometheus -config.file=/prometheus-data/prometheus.conf

Start mysql::

  docker run --name mysql --env MYSQL_ROOT_PASSWORD=CHANGEME --env MYSQL_DATABASE=promdash --env MYSQL_USER=promdash --env MYSQL_PASSWORD=CHANGEME mysql

Setup the promdash database::

  # Lookup the IP address allocated to mysql
  docker inspect mysql | grep IPAddress
  # Then peplace 172.17.0.7 with the allocated IP address
  docker run --rm true --env DATABASE_URL=mysql2://promdash:CHANGEME@172.17.0.7/database --env RAILS_ENV=production --link mysql:mysql --port 3000:3000 prom/promdash ./bin/rake db:migrate

Run promdash::

  docker run --name promdash --env DATABASE_URL=mysql2://promdash:CHANGEME@172.17.0.2/promdash --env RAILS_ENV=production --link mysql:mysql --port 3000:3000 prom/promdash

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

Monitoring logs
---------------

Metrics from logs are exported using
https://bitbucket.org/halfr/prometheus-journald

The prometheus metrics are available at ``http://MACHINE:9010``.

Monitoring machines
-------------------

Install https://aur.archlinux.org/packages/prometheus-node-exporter/ on all the
machines.

The prometheus metrics are available at ``http://MACHINE:9100``.
