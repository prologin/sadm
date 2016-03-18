The user database
=================

Data Structures
---------------

Each user has a:
- login
- first name
- last name
- uid
- group among user, orga and root
- password
- shell (default to bash)
- ssh key (public key of the user)
- realname, which is first + last name

Requests
--------

You can only query udb for an user, using the login, uid, group, shell or ssh key.
The request uses the django query syntax.

The server also exports metrics, and provides an administration pannel.

Client
------

The client object is ``udb.client._UDBClient(url, secret)``.
You have to instanciate one using ``udb.client.connect(auth=False)``, which will automatically pull the key from the config file.

Server
------

The server only returns passwords for authenticated users.

It also exports updates to udbsync using ``usb.receivers``.
