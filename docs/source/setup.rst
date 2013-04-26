Setup instructions
==================

If you are like the typical Prologin organizer, you're probably reading this
documentation one day before the start of the event, worried about your ability
to make everything work before the contest starts. Fear not! This section of
the documentation explain everything you need to do to set up the
infrastructure for the finals, assuming all the machines are already physically
present. Just follow the guide!

Last update: 2013.

Step 1: setting up the core services: MDB, DNS, DHCP
----------------------------------------------------

This is the first and trickiest part of the setup. As this is the core of the
architecture, everything kind of depends on each other:

.. image:: core-deps.png

Fortunately, we can easily work around these dependencies in the beginning.

All these core services will be running on ``gw.prolo``, the network gateway.
They could run elsewhere but we don't have a lot of free machines and the core
is easier to set up at one single place.

Basic system
~~~~~~~~~~~~

Start by installing a standard Arch system. We're going to have some network
related stuff to do, so rename the LAN interface to something with a
readable name::

  echo 'SUBSYSTEM=="net", ACTION=="add", ATTR{address}=="aa:bb:cc:dd:ee:ff",
  NAME="lan"' >> /etc/udev/rules.d/10-network.rules

Install a few packages we will need::

  pacman -S git dhcp bind python python-pip python-virtualenv libyaml nginx \
            sqlite dnsutils

Create the main Python ``virtualenv`` we'll use for all our Prologin apps::

  mkdir /var/prologin
  virtualenv3 --no-site-packages /var/prologin/venv

Enter the ``virtualenv``::

  source /var/prologin/venv/bin/activate

Clone the ``sadm`` repository, which contains everything we'll need to setup::

  git clone http://bitbucket.org/prologin/sadm
  cd sadm

Install the required Python packages::

  pip install -r requirements.txt

mdb
~~~

We now have a basic environment to start setting up services on our gateway
server. We're going to start by installing ``mdb`` and configuring ``nginx`` as
a reverse proxy for this application. Fortunately, a very simple script is
provided with the application in order to setup what it requires::

  python3 install.py mdb
  # Type 'no' when Django asks you to create a superuser.
  mv /etc/nginx/nginx.conf{.new,}
  # ^ To replace the default configuration by our own.

This command installed the ``mdb`` application to ``/var/prologin/mdb`` and
installed the ``systemd`` and ``nginx`` configuration files required to run the
application. You should be able to start ``mdb`` and ``nginx`` like this::

  systemctl enable mdb && systemctl start mdb
  systemctl enable nginx && systemctl start nginx

In order to test if ``mdb`` is working properly, we need to go to query
``http://mdb/`` with a command line tool like ``curl``. However, to get DNS
working, we need ``mdbdns``, which needs ``mdbsync``, which needs ``mdb``. As a
temporary workaround, we're going to add ``mdb`` to our ``/etc/hosts`` file::

  echo '127.0.0.1 mdb' >> /etc/hosts

Now you should get an empty list when querying ``/query``::

  curl http://mdb/query
  # Should return []

Congratulations, ``mdb`` is installed and working properly!

mdbsync
~~~~~~~

The next step now is to setup ``mdbsync``. ``mdbsync`` is a Tornado web server
used for applications that need to react on ``mdb`` updates. The DHCP and DNS
config generation scripts use it to automatically update the configuration when
``mdb`` changes. Once again, setting up ``mdbsync`` is pretty easy::

  python3 install.py mdbsync
  systemctl enable mdbsync && systemctl start mdbsync
  systemctl restart nginx
  echo '127.0.0.1 mdbsync' >> /etc/hosts

To check if ``mdbsync`` is working, try to register for updates::

  curl http://mdbsync/poll
  # Should return [] and keep the connection open

mdbdns
~~~~~~

``mdbdns`` gets updates from ``mdbsync`` and regenerates the DNS configuration.
Once again, an installation script is provided::

  python3 install.py mdbdns
  mv /etc/named.conf{.new,}
  # ^ To replace the default configuration by our own.
  systemctl enable mdbdns && systemctl start mdbdns
  systemctl enable named && systemctl start named

We now need to add a record in ``mdb`` for our current machine, ``gw.prolo``,
so that DNS configuration can be generated::

  cd /var/prologin/mdb
  python3 manage.py addmachine --hostname gw --mac 11:22:33:44:55:66 \
      --ip 192.168.1.254 --rfs 1 --hfs 1 --aliases mdb,mdbsync,ns \
      --mtype service --room pasteur

Once this is done, ``mdbdns`` should have automagically regenerated the DNS
configuration::

  host mdb.prolo 127.0.0.1
  # Should return 192.168.1.254

You can now remove the two lines related to ``mdb`` and ``mdbsync`` from your
``/etc/hosts`` file, and configure ``/etc/resolv.conf`` to use ``127.0.0.1`` as
your default DNS server::

  cat > /etc/resolv.conf <<EOF
  search prolo
  nameserver 127.0.0.1
  EOF

Step 2: building the iPXE bootrom
---------------------------------

The iPXE bootrom is an integral part of the boot chain for user machines. It is
loaded by the machine BIOS via PXE and is responsible for booting the Linux
kernel using the nearest RFS. It also handles registering the machine in the
MDB if needed.

iPXE is an external open source project, clone it first::

  git clone git://git.ipxe.org/ipxe.git

Then compile time settings need to be modified. Uncomment the following lines::

  // in config/general.h
  #define REBOOT_CMD

You can now build iPXE: go to ``src/`` and build the bootrom using our script
provided in ``prologin-sadm/netboot``::

  make bin/undionly.kpxe EMBED=/path/to/prologin-sadm/netboot/script.ipxe

Step 3: setting up the web services
------------

You can autoinstall ``paste`` and ``docs`` using::

  python3 install.py webservices

Then enable them::

  systemctl enable paste && systemctl start paste
  systemctl enable docs && systemctl start docs
