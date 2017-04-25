Disaster recovery
=================

What to do when something bad and unexpected happen.

Here are the rules:

#. Diagnose root cause, don't fix the consequences of a bigger failure.
#. Balance the "quick" and the "dirty" of your fixes.
#. Always document clearly and precisely what was wrong and what you did.
#. Don't panic!

Disk failure
------------

Hard fail
~~~~~~~~~

The ``md`` array will go into degraded mode. See ``/proc/mdstat``.

If the disk breaks when the system is powered off, the ``md`` array will start
in an inactive state and your will be dropped in the emergency shell. You will
have to re-activate the array to continue booting::

  $ mdadm --stop /dev/md127
  $ mdadm --assemble
  $ mount /dev/disk/by-label/YOUR_DISK_ROOT_LABEL new_root/
  $ exit  # exit the emergency shell and continue the booting sequence
