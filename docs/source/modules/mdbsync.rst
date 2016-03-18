mdbsync
=======
mdbsync is in charge of sending updates to the clients who suscribed to the state changes of mdb.

Client
------
The client is a prologin.synchronisation.Client instance looking for the mac in the backlog.

Server
------
The server is a ``prologin.synchronisation.Server`` subclass instance configured to use the mac as abacklog key, as well as pulling the initial backlog from mdb.

When the server is ran as a standalone program, is listens on port 8000 by default, using the port specified as the first argument otherwise.
