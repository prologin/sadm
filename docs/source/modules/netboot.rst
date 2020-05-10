The iPXE Script
===============

iPXE is a shell-like network bootloader scripting engine.

We use such a script for contestants machines to behave differently at boot
time depending on whether they're registered into ``mdb`` or not.

A server is started to proxy between the machines booting and the iPXE script,
as these aren't ineractive enough to query mdb.

Another iPXE script is returned by this server depending on the mdb answer.


TODO
Requires some work to undertand how it actually works
