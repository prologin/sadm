Running the websites without a complete SADM setup
==================================================

When hacking on the various web services included in SADM, it is not necessary
to setup a full-blown SADM infrastructure. Typically, when making the design of
``concours`` website for a new edition, only a small Django setup has to be
completed.

.. highlight:: bash

#. Clone SADM and cd into it::

     git clone https://github.com/prologin/sadm
     cd sadm

#. Configure the website::

     # for the 'concours' site
     vim etc/prologin/concours.yml

   Refer below for a guide of values to adapt depending on the website being
   worked on.

#. Create a venv (don't activate it yet)::

     python -m venv .venv

#. Add the configuration path to ``.venv/bin/activate`` so it is automatically
   set up when you activate the venv::

     echo "export CFG_DIR='$PWD/etc/prologin'" >> .venv/bin/activate

#. Activate the venv, install the requirements::

     source .venv/bin/activate
     pip install -r requirements.txt -e .

#. Apply the migrations, create a super-user and run::

     # for the 'concours' site
     cd django/concours
     python manage.py migrate
     python manage.py createsuperuser --username prologin --email x@prologin.org
     # fill in the password;
     python manage.py runserver

   Go to http://localhost:8000/, use ``prologin`` and the password you just
   chose to log in.

Working on ``concours``
-----------------------

Configuration
*************

Customize ``etc/prologin/concours.yml`` with the following:

``db.default``
   The easiest way is to use SQLite::

      ENGINE: django.db.backends.sqlite3
      NAME: concours.sqlite

``contest.game``
   Use the correct year, typically ``prologin2018`` for the 2018 edition.

``contest.directory``
   Use a writable directory, eg. ``/tmp/prologin/concours_shared``.

``website.static_path``
   Put the absolute path to ``prologin<year>/www/static`` or whatever
   directory is used for this edition.

Other ``contest`` entries (eg. ``use_maps``)
   Adapt to the correct settings for this edition.

Importing a stechec2 dump for testing
*************************************

When developing the Javascript replay and other features, you might need to import test dumps that
can be loaded on the website.

While in the correct virtualenv::

   cd django/concours
   python manage.py import_dump /path/to/my/dump.json

This will create a dummy match with zero players and no map, that will successfully load on the
dedicated URL. The match detail URL output by this command will only work in the default setup where
``manage.py runserver`` is used on ``localhost:8000``. Adapt the host/port if needed.
