Misc services
=============

``/sgoinfre``
-------------

Setup a ``rw`` nfs export on a ``misc`` machine, performance or reliabiliy is
not a priority for this service.

install `nfs-utils` on `misc`

Add the following line to /etc/exports
  /sgoinfre *(rw,insecure,squash_all,no_subtree_check,nohide)
Run the following commands on `misc`:
  exportfs -arv
  systemctl enable --now nfs-server

The following ``systemd`` service can be installed on the rhfs (in nfsroot)::

  # /etc/systemd/system/sgoinfre.mount
  [Unit]
  After=network-online.target

  [Mount]
  What=sgoinfre:/sgoinfre
  Where=/sgoinfre
  Options=nfsvers=4,nolock,noatime

  [Install]
  WantedBy=multi-user.target

Then enable the unit
  # systemctl enable --now sgoinfre.mount

doc
---

Setup::

  python install.py docs
  systemctl reload nginx

You have to retrieve the documentations of each language::

  pacman -S wget unzip
  su webservices - # So that the files have the right owner
  cd /var/prologin/docs/languages
  ./get_docs.sh

You can now test the docs:

- Open ``http://docs/languages/``
- Click on each language, you should see their documentation.

paste
-----

We will setup dpaste: https://github.com/bartTC/dpaste::

  pip install dpaste
  python install.py paste

  systemctl enable paste && systemctl start paste
  systemctl reload nginx

Redmine (a.k.a. "bugs")
-----------------------

First, export some useful variables. Change them if needed::

  export PHOME=/var/prologin
  export PGHOST=web  # postgres host
  export RUBYV=2.2.1
  export RAILS_ENV=production
  export REDMINE_LANG=fr
  read -esp "Enter redmine db password (no ' please): " RMPSWD

Download and extract Redmine::

  cd /tmp
  wget http://www.redmine.org/releases/redmine-3.0.1.tar.gz
  tar -xvz -C $PHOME -f redmine*.tar.gz
  mv $PHOME/{redmine*,redmine}

Using RVM, let's install dependencies::

  # Trust RVM keys
  curl -sSL https://rvm.io/mpapis.asc | gpg2 --import -
  curl -sSL https://get.rvm.io | bash -s stable
  source /etc/profile.d/rvm.sh
  echo "gem: --no-document" >>$HOME/.gemrc
  rvm install $RUBYV  # can be rather long
  rvm alias create redmine $RUBYV
  gem install bundler unicorn

Create the Redmine user and database::

  sed -e s/DEFAULT_PASSWORD/$RMPSWD/ /root/sadm/sql/redmine.sql | su - postgres -c psql

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

  bundle exec rake generate_secret_token
  bundle exec rake db:migrate
  bundle exec rake redmine:load_default_data

Create some dirs and fix permissions::

  mkdir -p $PHOME/redmine/{tmp,tmp/pdf,public/plugin_assets}
  chown -R redmine:http $PHOME/redmine
  chmod -R o-rwx $PHOME/redmine
  chmod -R 755 $PHOME/redmine/{files,log,tmp,public/plugin_assets}

Install the SSO plugin::

  ( cd $PHOME/redmine/plugins && git clone https://github.com/prologin/redmine-sso-auth.git )

Now it's time to install Redmine system configuration files. Ensure you are
within the prologin virtualenv (``source /opt/prologin/venv/bin/activate``), then::

  cd /root/sadm
  python install.py redmine udbsync_redmine

Register the new plugins (SSO, IRC hook)::

  ( cd $PHOME/redmine && exec rake redmine:plugins:migrate )
  # Should display:
  # Migrating issues_json_socket_send (Redmine issues to socket JSON serialized)...
  # Migrating redmine_sso_auth (SSO authentication plugin)...

Enable and start the services::

  systemctl enable redmine && systemctl start redmine
  systemctl enable udbsync_redmine && systemctl start udbsync_redmine
  systemctl reload nginx

You should be able to access the brand new Redmine. There are some important
configuration settings to change:

- Login at http://redmine/login with ``admin`` / ``admin``
- Change password at http://redmine/my/password
- In http://redmine/settings?tab=authentication
  - Enable enforced authentication.
  - Set minimum password length to 0.
  - Disable lost password feature, account deletion and registration.
- In http://redmine/settings/plugin/redmine_sso_auth
  - Enable SSO.
  - If not already done, set environment variable to ``HTTP_X_SSO_USER``.
  - Set search method to username.
- Configure a new project at http://redmine/projects/new
  The ``Identifiant`` **has to be ``prologin``** in order to vhosts to work.
- As soon as ``udbsync_redmine`` has finished its first sync, you should
  find the three groups (user, orga, root) at http://redmine/groups so
  you can give them special priviledges: click one, click the "Projets"
  tab, assign your "prologin" project to one of the roles. For instance:
  user → ∅, orga → developer, root → {manager, developer}

Homepage
--------

The homepage links to all our web services. It is a simple Django app that
allows adding links easily. Setup it using ``install.py``::

  python install.py homepage
  systemctl enable homepage && systemctl start homepage
  systemctl enable udbsync_django@homepage && systemctl start udbsync_django@homepage

You can then add links to the homepage by going to http://homepage/admin.

DJ-Ango
-------

See dj_ango README: https://bitbucket.org/Zeletochoy/dj-ango/

IRC
---

Install the ircd, then install the config::

  pacman -S unrealircd
  python install.py ircd
  mv /etc/unrealircd/unrealircd.conf{.new,}

Change the OPER password in the config::

  vim /etc/unrealircd/unrealircd.conf

Then enable and start the IRCd::

  systemctl enable --now unrealircd

Now you need to enable the SOCKS tunnel so that IRC is available from the
outside. First, generate a ssh key in misc, and add it to an user of the
public-facing server (e.g prologin.org)::

  ssh-keygen -t ed25519 -q -N "" < /dev/zero
  ssh-copy-id dev@prologin.org

Then, enable and start the IRC gatessh::

  systemctl enable --now irc_gatessh

IRC issues bot
~~~~~~~~~~~~~~

Once both IRC and Redmine are installed, you can also install the IRC bot that
warns about new issues::

  python install.py irc_redmine_issues
  systemctl enable --now irc_redmine_issues
