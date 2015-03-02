Setup instructions
==================

If you are like the typical Prologin organizer, you're probably reading this
documentation one day before the start of the event, worried about your ability
to make everything work before the contest starts. Fear not! This section of
the documentation explain everything you need to do to set up the
infrastructure for the finals, assuming all the machines are already physically
present. Just follow the guide!

Mainteners:

- Alexandre Macabies (2013, 2014)
- Antoine Pietri (2013, 2014)
- Marin Hannache (2013, 2014)
- Pierre Bourdon (2013, 2014)
- Paul Hervot (2014)
- Rémi Audebert (2014)
- Nicolas Hureau (2013)
- Pierre-Marie de Rodat (2013)
- Sylvain Laurent (2013)

Step 0: hardware and network setup
----------------------------------

Before installing servers, we need to make sure all the machines are connected
to the network properly. Here are the major points you need to be careful
about:

* Make sure to balance the number of machines connected per switch: the least
  machines connected to a switch, the better performance you'll get.
* Inter-switch connections is not very important: we tried to make most things
  local to a switch (RFS + HFS should each be local, the rest is mainly HTTP
  connections to services).

For each pair of switches, you will need one RHFS server (connected to the 2
switches via 2 separate NICs, and hosting the RFS + HFS for the machines on
these 2 switches). Please be careful out the disk space: assume that each RHFS
has about 100GB usable for HFS storage. That means at most 50 contestants (2GB
quota) or 20 organizers (5GB quota) per RHFS. With contestants that should not
be a problem, but try to balance organizers machines as much as possible.

You also need one gateway/router machine, which will have 3 different IP
addresses for the 3 logical subnets used during the finals:

:Users and services: 192.168.0.0/23
:Alien (unknown): 192.168.250.0/24
:Upstream: Based on the IP used by the bocal internet gateway.

Contestants and organizers must be on the same subnet in order for UDP
broadcasting to work between them. This is required for most video games played
during the finals: server browsers work by sending UDP broadcast announcements.

Having services and users on the same logical network avoids all the traffic
from users to services going through the gateway. Since this includes all RHFS
traffic, we need to make sure this is local to the switch and not being routed
via the gateway. However, for clarity reasons, we allocate IP addresses in the
users and services subnet like this:

:Users: 192.168.0.0 - 192.168.0.253
:Services and organizers machines: 192.168.1.0 - 192.168.1.253

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

.. note::

    (prologin2014) For some unknown reason, renaming interfaces did not work on
    all the NIC we had. For more information: see halfr or delroth

Update pacman packages and install a few packages we will need::

  pacman -Sy
  pacman -S git dhcp bind python python-pip python-virtualenv libyaml nginx \
            sqlite dnsutils rsync postgresql-libs tcpdump base-devel pwgen \
            libxslt ipset pssh postgresql nbd wget strace ntp tftp-hpa

Create the main Python ``virtualenv`` we'll use for all our Prologin apps::

  mkdir /var/prologin
  virtualenv3 --no-site-packages /var/prologin/venv

Enter the ``virtualenv``::

  source /var/prologin/venv/bin/activate

Clone the ``sadm`` repository, which contains everything we'll need to setup::

  git clone http://bitbucket.org/prologin/sadm
  cd sadm

Install the required Python packages::

  export C_INCLUDE_PATH=/usr/include/libxml2 # fix for archlinux
  pip install -r requirements.txt

mdb
~~~

We now have a basic environment to start setting up services on our gateway
server. We're going to start by installing ``mdb`` and configuring ``nginx`` as
a reverse proxy for this application. Fortunately, a very simple script is
provided with the application in order to setup what it requires::

  python install.py mdb
  mv /etc/nginx/nginx.conf{.new,}
  # ^ To replace the default configuration by our own.
  # Use python manage.py createsuperuser in /var/prologin/mdb to create a root

This command installed the ``mdb`` application to ``/var/prologin/mdb`` and
installed the ``systemd`` and ``nginx`` configuration files required to run the
application.

Don't forget to change the ``secret_key`` used by Django and the
``shared_secret`` used for ``mdb`` to ``mdbsync`` pushes::

  $EDITOR /etc/prologin/mdb-server.yml
  $EDITOR /etc/prologin/mdbsync-pub.yml

You should be able to start ``mdb`` and ``nginx`` like this::

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

  python install.py mdbsync

  systemctl enable mdbsync && systemctl start mdbsync
  systemctl reload nginx
  echo '127.0.0.1 mdbsync' >> /etc/hosts

To check if ``mdbsync`` is working, try to register for updates::

  python -c 'import prologin.mdbsync.client; prologin.mdbsync.client.connect().poll_updates(print)'
  # Should print {} {} and wait for updates

mdbdns
~~~~~~

``mdbdns`` gets updates from ``mdbsync`` and regenerates the DNS configuration.
Once again, an installation script is provided::

  python install.py mdbdns
  mv /etc/named.conf{.new,}
  # ^ To replace the default configuration by our own.
  systemctl enable mdbdns && systemctl start mdbdns
  systemctl enable named && systemctl start named

We now need to add a record in ``mdb`` for our current machine, ``gw.prolo``,
so that DNS configuration can be generated::

  cd /var/prologin/mdb
  python manage.py addmachine --hostname gw --mac 11:22:33:44:55:66 \
      --ip 192.168.1.254 --rfs 0 --hfs 0 --mtype service --room pasteur \
      --aliases mdb,mdbsync,ns,netboot,udb,udbsync,presencesync

.. note::

  If the gw does not have IP ``192.168.1.254``, use the following command to
  add it::

    ip link set dev <INTERACE> up
    ip addr add 192.168.1.254/23 dev <INTERFACE>

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

mdbdhcp
~~~~~~~

``mdbdhcp`` works just like ``mdbdns``, but for DHCP. You must edit
``dhcpd.conf`` to add an empty subnet for the IP given by the Bocal. If it is
on the same interface as 192.168.0.0/23, add it inside the ``shared-network``
``prolo-lan``, else add it to a new ``shared-network``::

  $EDITOR etc/dhcpd.conf
  python install.py mdbdhcp
  mv /etc/dhcpd.conf{.new,}
  # ^ To replace the default configuration by our own.
  systemctl enable mdbdhcp && systemctl start mdbdhcp
  systemctl enable dhcpd4 && systemctl start dhcpd4

netboot
~~~~~~~

Netboot is a small HTTP service used to handle interactions with the PXE boot
script: machine registration and serving kernel files. Once again, very simple
setup::

  python install.py netboot
  systemctl enable netboot && systemctl start netboot
  systemctl reload nginx

TFTP
~~~~

The TFTP server is used by the PXE clients to fetch the first stage of the boot
chain: the iPXE binary (more on that in the next section). We simply setup
``tftp-hpa``::

  systemctl enable tftpd.socket && systemctl start tftpd.socket

The TFTP server will serve files from ``/srv/tftp``.

iPXE bootrom
~~~~~~~~~~~~

The iPXE bootrom is an integral part of the boot chain for user machines. It is
loaded by the machine BIOS via PXE and is responsible for booting the Linux
kernel using the nearest RFS. It also handles registering the machine in the
MDB if needed. These instructions need to be run on ``gw``.

iPXE is an external open source project, clone it first::

  git clone git://git.ipxe.org/ipxe.git

Then compile time settings need to be modified. Uncomment the following lines::

  // in src/config/general.h
  #define REBOOT_CMD
  #define PING_CMD

You can now build iPXE: go to ``src/`` and build the bootrom, embedding our
script::

  make bin/undionly.kpxe EMBED=/root/sadm/python-lib/prologin/netboot/script.ipxe
  cp bin/undionly.kpxe /srv/tftp/prologin.kpxe

udb
~~~

Install ``udb`` using the ``install.py`` recipe::

  python install.py udb
  systemctl enable udb && systemctl start udb
  systemctl reload nginx

You can then import all contestants information to ``udb`` using the
``batchimport`` command::

  cd /var/prologin/udb
  python manage.py batchimport --file=/root/finalistes.txt
  # Use python manage.py createsuperuser to create a root

The password sheet data can then be generated with this command, then printed
by someone else::

  python manage.py pwdsheetdata --type=user > /root/user_pwdsheet_data

Then do the same for organizers::

  python manage.py batchimport --logins --type=orga --pwdlen=10 \
      --uidbase=11000 --file=/root/orgas.txt
  python manage.py pwdsheetdata --type=orga > /root/orga_pwdsheet_data

udbsync
~~~~~~~

Again, use the ``install.py`` recipe::

  python install.py udbsync
  systemctl enable udbsync && systemctl start udbsync
  systemctl reload nginx

Edit the shared secret::

  $EDITOR /etc/prologin/udbsync-sub.yml
  $EDITOR /etc/prologin/udbsync-pub.yml

We can then configure udbsync clients::

  python install.py udbsync_django udbsync_rootssh
  systemctl enable udbsync_django@mdb && systemctl start udbsync_django@mdb
  systemctl enable udbsync_django@udb && systemctl start udbsync_django@udb
  systemctl enable udbsync_rootssh && systemctl start udbsync_rootssh

presencesync
~~~~~~~~~~~~

And once again::

  python install.py presencesync
  systemctl enable presencesync && systemctl start presencesync
  systemctl reload nginx

Edit the shared secret::

  $EDITOR /etc/prologin/presencesync-sub.yml
  $EDITOR /etc/prologin/presencesync-pub.yml

Gateway network configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*gw* has three ips:

- 192.168.1.254/23 used to communicate with both the services and the users
- 192.168.250.254/24 used to communicate with aliens (aka. machines not in mdb)
- ?.?.?.?/? static IP given by the bocal to communicate with the bocal gateway

.. note::

    Make sure that the interfaces managed by netctl are down and don't have IP
    addresses assigned to them.

Setup the network interface, the netctl config file is located in
``etc/netctl/gw``, you may need to edit the ``Interface=`` line, add the static
IP given by the bocal and add a ``Gateway=`` line for the default gateway IP::

  python install.py netctl_gw
  netctl enable gw && netctl start gw

iptables
````````

.. note::

    If the upstream of gw.prolo is on a separate NIC you should replace
    etc/iptables with etc/iptables_upstream_nic.save

The name of the interface is hardcoded in the iptables configuration, you
should edit it to match your setup::

  $EDITOR etc/iptables.save

Setup the iptables rules and ipset creation for users allowed internet acces::

  python install.py firewall
  systemctl enable firewall && systemctl start firewall

And the service that updates these rules::

  python install.py presencesync_firewall
  systemctl enable presencesync_firewall && systemctl start presencesync_firewall

Step 2: file storage
--------------------

.. sidebar:: rhfs naming scheme

    A rhfs has two NIC and is connected to two switches, there is therefore two
    ``hfs-server`` running on one rhfs machine, each with a different id. The
    hostname of the rhfs that hosts hfs ``0`` and hfs ``1`` will have the
    following hostname: ``rhfs01``.


TODO: setting up ``rhfs0`` + instructions to setup other ``rhfs`` machines and
sync them.

Step 3: booting the user machines
---------------------------------

Note: if you are good at typing on two keyboards at once, or you have a spare
root doing nothing, this step can be done in parallel with step 4.

Installing the base user system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _ArchLinux Diskless Installation: https://wiki.archlinux.org/index.php/Diskless_network_boot_NFS_root#Bootstrapping_installation

The basic install process is already documented through the
`ArchLinux Diskless Installation`_. For conveniance, use::

  python install.py udbsync_rfs
  python install.py rfs

The installation script will bootstrap a basic archlinux system in
``/export/nfsroot`` with a few packages, a prologin hook that creates tmpfs at
``/var/{log,tmp,spool/mail}``, libprologin and some sadm services
(udbsync_passwd, udbsync_rootssh and presenced)

You should then install some useful packages for the contestants (see
``rfs/contestants_package_list`` file).

To install a new package (*never* use arch-chroot)::

  pacman --root /export/nfsroot -Sy package

TODO: How to sync, hook to generate /var...

Copying the kernel and initramfs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You might have to build another kernel if the contestants machines are not the
same.

::

  scp rhfs:/export/nfsroot/boot/vmlinuz-linux /srv/tftp/kernel
  scp rhfs:/export/nfsroot/boot/initramfs-linux.img /srv/tftp/initrd

Setting up hfs
~~~~~~~~~~~~~~

Setup postgresql on ``web``. It is used by all the hfs.

.. note::

  If you just want to test the ``hfs`` and have not yet setup ``web``, install
  the database on ``gw`` and add ``db`` to the list of aliases of ``gw``.

  The database should be on ``web`` because most of its consumers are
  webservices: redmine, concours, masterworker, etc.

Setup postgresql
````````````````

Create a new database::

  su - postgres -c "initdb --locale en_US.UTF-8 -D '/var/lib/postgres/data'"

Edit and uncomment ``/var/lib/postgres/data/postgresql.conf`` to make
postgresql listen on every interface::

  listen_addresses = '*'

And edit ``/var/lib/postgres/data/pg_hba.conf`` in order to allow all users
to connect with password::

  host     all             all             192.168.1.0/24           password

Then start postgresql::

  systemctl enable postgresql && systemctl start postgresql

Create user ``hfs``, database ``hfs``, and associated tables:

.. note::

    You must change the password of user ``hfs`` in ``sql/hfs.sql`` to match
    the one in ``etc/prologin/hfs-server.yml``.

::

  su - postgres -c "psql" < ./sql/hfs.sql

On every ``rhfs`` machine, install the hfs server::

  python install.py hfs
  # Change HFS_ID to what you need
  systemctl enable hfs@HFS_ID && systemctl start hfs@HFS_ID


Enable forwarding of authorized_keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On a rhfs, the service ``rootssh`` (aka. ``udbsync_clients.rootssh``) writes
the ssh public keys of roots to ``/root/.ssh/authorized_keys``. The unit
``rootssh.path`` watches this file, and on change starts the service
``rootssh-copy`` that updates the ``authorized_keys`` in the
``/exports/nfsroot``.

::

  systemctl enable rootssh.path && systemctl start rootssh.path

Step 4: setting up the web services
-----------------------------------

Requirements::

  pacman -S nginx

The web services will usually be set up on a separate machine from the ``gw``,
for availability and performance reasons (all services on ``gw`` are critical,
so you wouldn't want to mount a NFS on it for example). This machine is usually
named ``web.prolo``.

Once again, set up a standard Arch system. Then register it on ``mdb``, via the
web interface, or using::

  source /var/prologin/venv/bin/activate
  cd /var/prologin/mdb
  python manage.py addmachine --hostname web --mac 11:22:33:44:55:66 \
      --ip 192.168.1.100 --rfs 0 --hfs 0 \
      --aliases db,concours,wiki,bugs,redmine,docs,home,paste,map \
      --mtype service --room pasteur

When this is done, reboot ``web``: it should get the correct IP address from
the DHCP server, and should be able to access the internet. Proceed to setup a
virtualenv in ``/var/prologin/venv`` and clone the sadm repository by following
the same instructions given for ``gw`` ("Basic system" part).

Then, install the ``nginx`` configuration from the repository::

  python install.py nginxcfg
  mv /etc/nginx/nginx.conf{.new,}
  systemctl enable nginx && systemctl start nginx

Autoinstall
~~~~~~~~~~~

You can autoinstall some services and configuration files::

  python install.py webservices
  systemctl reload nginx

concours
~~~~~~~~

.. note::

    Concours is a *contest* service. See :ref:`enable_contest_services`.

Setup the database::

  su - postgres -c "psql" < ./sql/concours.sql

Install it::

  python install.py concours
  systemctl reload nginx

doc
~~~

You have to retrieve the documentations of each language::

  pacman -S wget unzip
  cd /var/prologin/docs/languages
  su webservices # So we don't have to change permissions afterwards
  ./get_docs.sh

TODO: stechec2 docs, sadm docs

paste
~~~~~

We will setup dpaste: https://github.com/bartTC/dpaste::

  # Switch to a special venv
  virtualenv3 --no-site-packages /var/prologin/venv_paste
  source /var/prologin/venv_paste/bin/activate
  pip install dpaste gunicorn
  # Back to the normal venv
  source /var/prologin/venv/bin/activate
  python install.py paste

wiki
~~~~

Download and install the MoinMoin archlinux package, and its dependancies::

  pacman -S python2 moinmoin gunicorn
  mkdir -p /var/prologin/wiki
  cp -r /usr/share/moin /var/prologin/wiki/

Then install the WSGI file::

  cd /var/prologin/wiki/moin
  cp server/moin.wsgi ./moin.py

Edit ``moin.py`` to set the path to the wiki configuration directory:
uncomment the line after ``a2)`` and modify it like this::

  sys.path.insert(0, '/var/prologin/wiki/moin')

Copy the wiki configuration file::

  cp webservices/wiki/wikiconfig.py /var/prologin/wiki

Fix permissions::

  chown -R webservices:webservices /var/prologin/wiki
  chmod o-rwx -R /var/prologin/wiki

Create the ``prologin`` super-user::

  PYTHONPATH=/var/prologin/wiki:$PYTHONPATH                              \
  moin --config-dir=/var/prologin/wiki account create --name prologin    \
       --alias prologin --password **CHANGEME** --email prologin@example.com

Add users in the sadm folder (TODO: will be obsolete with udbsync)::

  webservices/wiki/create_users.sh < passwords.txt

Then you can just start the service::

  systemctl enable wiki && systemctl start wiki

Redmine (a.k.a. "bugs")
~~~~~~~~~~~~~~~~~~~~~~~

First, export some useful variables. Change them if needed::

  export PHOME=/var/prologin
  export PGHOST=db  # postgres host
  export RUBYV=2.0.0-p451
  export RAILS_ENV=production
  export REDMINE_LANG=fr
  read -esp "Enter redmine db password (no ' please): " RMPSWD

Download and extract Redmine::

  cd /tmp
  wget http://www.redmine.org/releases/redmine-2.5.1.tar.gz
  tar -xvz -C $PHOME -f redmine-2.5.1.tar.gz
  mv $PHOME/{redmine*,redmine}

Using RVM, let's install dependencies::

  curl -L http://get.rvm.io | bash -s stable
  source /etc/profile.d/rvm.sh
  echo "gem: --no-document" >>$HOME/.gemrc
  rvm install $RUBYV  # can be rather long
  rvm alias create redmine $RUBYV
  gem install -v 1.4.5 rack  # unicorn installs a newer version Redmine doesn't like
  gem install bundler unicorn

Create the Redmine user and database (user may not be postgres)::

  sed -e s/%pwd%/$RMPSWD/ $PHOME/sadm/sql/redmine.sql | psql -U postgres -h $PGHOST

Configure the Redmine database::

  cat >$PHOME/redmine/config/database.yml <<EOF
  # prologin redmine database
  production:
    adapter: postgresql
    database: redmine
    host: $PGHOST
    username: redmine
    password: $RMPSWD
    encoding: utf8
  EOF

We can now install Redmine::

  cd $PHOME/redmine
  bundle install --without development test rmagick

Some fixtures (these commands require the above env vars)::

  rake generate_secret_token
  rake db:migrate
  rake redmine:load_default_data

Create some dirs and fix permissions::

  mkdir -p $PHOME/redmine/{tmp,tmp/pdf,public/plugin_assets}
  chown -R redmine:redmine $PHOME/redmine
  chmod -R o-rwx $PHOME/redmine
  chmod -R 755 $PHOME/redmine/{files,log,tmp,public/plugin_assets}

Now it's time to install Redmine system configuration files. Ensure you are
within the prologin virtualenv (``source /var/prologin/venv/bin/activate``), then::

  cd $PHOME/sadm
  python install.py redmine udbsync_redmine

Enable and start the services::

  systemctl enable redmine && systemctl start redmine
  systemctl enable udbsync_redmine && systemctl start udbsync_redmine

You should be able to access the brand new Redmine.

- Login at http://redmine/login with ``admin`` / ``admin``
- Change password at http://redmine/my/password
- Configure a new project at http://redmine/projects/new
  The ``Identifiant`` **has to be ``prologin``** in order to vhosts to work.
- As soon as `udbsync_redmine` has finished its first sync, you should
  find the three groups (user, orga, root) at http://redmine/groups so
  you can give them special priviledges: click one, click the "Projets"
  tab, assign your "prologin" project to one of the roles. For instance:
  user → ∅, orga → developer, root → manager ∪ developer

Homepage
~~~~~~~~

The homepage links to all our web services. It is a simple Django app that
allows adding links easily. Setup it using ``install.py``::

  python install.py homepage
  systemctl enable homepage && systemctl start homepage
  systemctl enable udbsync_django@homepage && systemctl start udbsync_django@homepage

You can then add links to the homepage by going to http://homepage/admin.

Step 5: Misc services
---------------------

DJ-Ango
-------

See dj_ango README: https://bitbucket.org/Zeletochoy/dj-ango/

IRC
~~~

TODO

Notify bot
~~~~~~~~~~

You should install the ``pypeul`` python library and the ``python-gobject`` and
``libnotify`` archlinux packages first on the RFS. Then, copy notify-bot.py to
``/usr/share/notify-bot.py``.

The notify bot must be started after being logged in KDM. Add this line to
the ``.xsession`` of the users home skeleton::

  python /usr/share/libnotify.py &

Step 6: Switching to contest mode
---------------------------------

Block internet access
~~~~~~~~~~~~~~~~~~~~~

Edit ``/etc/prologin/presencesync_firewall.yml`` and remove the ``user`` group,
the restart ``presencesync_firewall``.

.. _enable_contest_services:

Enable contest services
~~~~~~~~~~~~~~~~~~~~~~~

By default, most of the web services are hidden from the contestants. In order
to show them, you must activate the "contest mode" in some service.

Edit ``/etc/nginx/nginx.conf``, uncomment the following line::

  # include services_contest/*.nginx;

Reset the hfs
~~~~~~~~~~~~~

If you need to delete every /home created by the hfs, simply delete all nbd
files in ``/export/hfs/`` and delete entries in the ``user_location`` table of
the hfs' database.

::

  # For each hfs instance
  rm /export/hfs/*.nbd

::

  su - postgres -c 'psql hfs'
  delete from user_location;

And finally, empty the nbd's configuration so it can take it's arguments only
from the command line::

  echo "[generic]" > /etc/nbd-server/config

.. todo::

    Setup alternate skeleton.
