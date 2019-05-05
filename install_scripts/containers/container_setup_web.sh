#!/bin/bash

# Configuration variables
CONTAINER_NAME=myweb

CONTAINER_HOSTNAME=web
CONTAINER_MAIN_IP=192.168.1.100
MDB_ALIASES=db,concours,wiki,bugs,redmine,docs,home,paste,map,masternode

GW_CONTAINER_NAME=mygw

source ./container_setup_common.sh

container_script_header

# Setup stages
function stage_setup_network {
  echo_status 'Stage setup network'

  echo '[-] Install SADM network setup'
  container_run /var/prologin/venv/bin/python /root/sadm/install.py systemd_networkd_web nic_configuration
  # Skipped as the container's virtual interface does not support the tweaks we apply
  skip container_run /usr/bin/systemctl enable --now nic-configuration@host0

  echo '[-] Restart systemd-networkd'
  container_run /usr/bin/systemctl restart systemd-networkd

  container_snapshot $FUNCNAME
}

function test_network {
  echo '[>] Test network... '

  echo -n '[>] Check internet access '
  test_url https://gstatic.com/generate_204

  echo -n '[>] Check web.prolo IPs '
  if ! machinectl status $CONTAINER_NAME | grep -q "Address: $CONTAINER_MAIN_IP"; then
    echo_ko "FAIL"
    return 1
  else
    echo_ok "PASS"
  fi
}

function stage_setup_web {
  echo_status 'Run web setup script'

  container_run /root/sadm/install_scripts/setup_web.sh

  container_snapshot $FUNCNAME
}

function stage_setup_udbsync_rootssh {
  echo_status "Setup udbsync_rootssh"

  container_run /var/prologin/venv/bin/python /root/sadm/install.py udbsync_rootssh
  container_run /usr/bin/systemctl enable --now udbsync_rootssh

  container_snapshot $FUNCNAME
}

function test_udbsync_rootssh {
  echo '[>] Test udbsync_rootssh... '

  test_service_is_enabled_active udbsync_rootssh

  #TODO more tests
}

function stage_setup_concours {
  echo_status "Setup concours"

  container_run /var/prologin/venv/bin/python /root/sadm/install.py concours
  container_run /usr/bin/systemctl enable --now concours
  container_run /usr/bin/systemctl enable --now udbsync_django@concours

  sed 's/# include services_contest/include services_contest/' -i $CONTAINER_ROOT/etc/nginx/nginx.conf

  container_run /usr/bin/systemctl reload nginx

  # Give concours some time to start
  sleep 3

  container_snapshot $FUNCNAME
}

function test_concours {
  echo "[>] Test concours..."

  test_service_is_enabled_active concours
  test_service_is_enabled_active udbsync_django@concours

  test_url http://concours/
}

function stage_setup_homepage {
  echo_status "Setup homepage"

  container_run /var/prologin/venv/bin/python /root/sadm/install.py homepage
  container_run /usr/bin/systemctl enable --now homepage
  container_run /usr/bin/systemctl enable --now udbsync_django@homepage

  container_run /usr/bin/systemctl reload nginx

  # Give homepage some time to start
  sleep 3

  container_snapshot $FUNCNAME
}

function test_homepage {
  echo "[>] Test homepage..."

  test_service_is_enabled_active homepage
  test_service_is_enabled_active udbsync_django@homepage

  test_url http://home/
}

function stage_setup_masternode {
  echo_status "Setup masternode"

  container_run /var/prologin/venv/bin/python /root/sadm/install.py masternode
  container_run /usr/bin/systemctl enable --now masternode

  container_snapshot $FUNCNAME
}

function test_masternode {
  echo "[>] Test masternode..."

  test_service_is_enabled_active masternode
}

function stage_setup_redmine {
  echo_status "Setup redmine"

  container_run /var/prologin/venv/bin/python /root/sadm/install.py redmine

  cat > $CONTAINER_ROOT/root/setup_redmine.sh <<EOF
#!/bin/bash

set -e

export PHOME=/var/prologin
export PGHOST=web  # postgres host
export RUBYV=2.2.1
export RAILS_ENV=production
export REDMINE_LANG=fr
export RMPSWD=$ROOT_PASSWORD

cd /tmp
wget --continue http://www.redmine.org/releases/redmine-3.0.1.tar.gz
tar -xvz -C \$PHOME -f redmine*.tar.gz
mv \$PHOME/{redmine*,redmine}

curl -sSL https://rvm.io/mpapis.asc | gpg2 --import -
curl -sSL https://get.rvm.io | bash -s stable
source /etc/profile.d/rvm.sh
echo "gem: --no-document" >>\$HOME/.gemrc
rvm install \$RUBYV  # can be rather long
rvm alias create redmine \$RUBYV
gem install bundler unicorn

# TODO move this to install.py to replace secret
sed -e s/DEFAULT_PASSWORD/\$RMPSWD/ /root/sadm/sql/redmine.sql | su - postgres -c psql

cat >\$PHOME/redmine/config/database.yml <<EOFF
# prologin redmine database
production:
  adapter: postgresql
  jdatabase: redmine
  host: \$PGHOST
  username: redmine
  password: \$RMPSWD
  encoding: utf8
EOFF

cd \$PHOME/redmine
bundle install --without development test rmagick

bundle exec rake generate_secret_token
bundle exec rake db:migrate
bundle exec rake redmine:load_default_data

mkdir -p \$PHOME/redmine/{tmp,tmp/pdf,public/plugin_assets}
chown -R redmine:http \$PHOME/redmine
chmod -R o-rwx \$PHOME/redmine
chmod -R 755 \$PHOME/redmine/{files,log,tmp,public/plugin_assets}

( cd \$PHOME/redmine/plugins && git clone https://github.com/prologin/redmine-sso-auth.git )

cd /root/sadm
python install.py redmine udbsync_redmine

( cd \$PHOME/redmine && exec rake redmine:plugins:migrate )

systemctl enable redmine && systemctl start redmine
systemctl enable udbsync_redmine && systemctl start udbsync_redmine
systemctl reload nginx
EOF

  chmod +x $CONTAINER_ROOT/root/setup_redmine.sh
  container_run /root/setup_redmine.sh

  container_snapshot $FUNCNAME
}

function test_redmine {
  echo "[>] Test redmine..."

  test_service_is_enabled_active redmine udbsync_redmine
}


if ! machinectl >/dev/null status $GW_CONTAINER_NAME; then
  echo >&2 "Please start the GW container"
  # TODO: using a VM for GW is also doable, should allow it
  exit 1
fi

# "container" script
run container_stop
run stage_setup_container
run stage_bootstrap_arch_linux
run container_start

run stage_add_to_mdb
run container_stop
run container_start

run stage_allow_root_ssh

run stage_copy_sadm

run stage_setup_sadm
run test_sadm

run stage_setup_web

run stage_setup_libprologin
run test_libprologin

run stage_setup_udbsync_rootssh
run test_udbsync_rootssh

run stage_setup_network
run test_network
run test_local_network
run test_internet

run stage_setup_nginx
run test_nginx

run stage_setup_postgresql
run test_postgresql

run stage_setup_concours
run test_concours

run stage_setup_homepage
run test_homepage

run stage_setup_masternode
run test_masternode

# Skipped as not ready yet
skip stage_setup_redmine
skip test_redmine

echo_status "$CONTAINER_HOSTNAME setup: success!"
