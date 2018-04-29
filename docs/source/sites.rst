Running the websites without SADM
======================================

0. Clone SADM and cd into it 

.. code-block:: bash

  git clone https://github.com/prologin/sadm
  cd sadm

1. Create a venv and activate it

.. code-block:: bash

  python -m venv .venv
  source .venv/bin/activate

2. Install requirements

.. code-block:: bash

  pip install -r requirements.txt
  pip install -e python-lib

3. Configure the databases (refer to the `Django documentation`_ if you need help)

.. code-block:: bash

  # for the 'concours' site
  vim etc/prologin/concours.yml

4. Add the configuration path to ``.venv/bin/activate`` so it is automatically run when you activate the venv

.. code-block:: bash

  deactivate
  echo "export CFG_DIR=\"$PWD/etc/prologin\"" >> .venv/bin/activate
  source .venv/bin/activate

5. Apply the migrations, create a super user and run!

.. code-block:: bash

  # for the 'concours' site
  cd django/concours
  python manage.py migrate
  python manage.py createsuperuser
  # fill in the fields
  python manage.py runserver
  # you did it!

_`Django documentation`: https://docs.djangoproject.com/en/1.11/ref/settings/#databases 
