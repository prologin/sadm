Presence Services
=================
if order to log connections and disconnections, we do have a pam module that tracks it and perform the appropriate background actions:
- Try to authentify the user with udb. This is done thanks to pam_unix.so, as the users are synchronized between root filesystems.
- If it succeeds, and it's a connection, request a home migration and mount the home.
- If it's a disconnection, unmount the home.

There is a daemon running on the machines, called presenced, which is periodically sending a heartbeat to another daemon, called presencesync.

Requests to presencesync are done using a client connecting to presenced.
  
TODO:
ask for precisions about the role of presenced and presencesync, make a flowchart of the login process
