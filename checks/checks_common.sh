# Logging functions
function echo_status {
 # blue foreground, then default foreground
  echo -e "\e[34m[+] $*\e[39m"
}

function echo_ko {
  # red foreground, then default foreground
  echo -e "\e[31m$*\e[39m"
}

function echo_ok {
  # green foreground, then default foreground
  echo -e "\e[32m$*\e[39m"
}

function test_service_is_enabled_active {
  service=$1
  service_status=$(systemctl is-active $service)

  echo -n "$service is $service_status "
  if [[ $service_status == active ]]; then
    echo_ok "OK"
  else
    echo_ko "FAIL: should be active"
  fi

  service_status=$(systemctl is-enabled $service)
  echo -n "$service is $service_status "
  if [[ $service_status == enabled ]]; then
    echo_ok "OK"
  else
    echo_ko "FAIL: should be enabled"
  fi
}

function test_file_present {
  filename=$1
  echo -n "$filename is "
  if [[ -e $filename ]]; then
    echo_ok "present"
  else
    echo_ko "absent"
  fi
}

function check_ip {
  ip_addr=$1

  echo -n "$ip_addr is "
  ips=$(ip addr show | grep 'inet ')
  if echo $ips | grep -q $ip_addr; then
    echo_ok "present"
  else
    echo_ko "absent"
  fi
}

function not_in_alien_subnet {
  echo -n "System is not in the alien subnet... "

  if ip addr show | grep 'inet 192.168.250'; then
    echo_ko "FAIL (has alien ip)"
    return 1
  fi

  if ip route show | grep '192.168.250'; then
    echo_ko "FAIL (has alien route)"
    return 1
  fi

  echo_ok "OK"
}

function check_hostname {
  ref_hostname=$1

  if [[ $(hostname) != $ref_hostname ]]; then
    echo_ok "Hostname is $ref_hostname"
  else
    echo_ko "Hostname is $(hostname), should be $ref_hostname"
  fi
}
