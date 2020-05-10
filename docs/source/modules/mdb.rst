Structure of mdb
================

Mdb can handle two types of requests:

- query for a machine
- add one


Client
------

Mdb includes a library to interact with it.

using the connect() function creates a MDBClient holding the connection url.

Requests
~~~~~~~~

- Queries are POSTs to /query with a single 'data' field containing the django
  database query arguments. They return json dump of a list of machines.

- Registrations are GETs to /register with the query string as argument. They
  return the allocated ip.

Server
------
It also exports metrics thanks to django_prometheus, as well a django admin pannel.

You can manage the IP pools as well as the machines in the admin pannel.

### Data structures (models.py)

Each machine has:

- a hostname
- some aliases
- an ip
- a mac address
- a rfs
- a hfs

- a machine type among the following:

 - user
 - orga
 - cluster
 - service

- a room among the following:

 - pasteur
 - cluster
 - alternative room
 - other

There's a global list of ip pools, one for each machine type.
They all have:
- an assigned type
- a network
- a last allocation remainder

Update feed
~~~~~~~~~~~
updates are sent to mdbsync using ``mdbsync.client``.
It can either be updates or deletions.

``mdbsync.client`` isn't a class, ``connect`` returns a
``synchronisation.Client`` object.
