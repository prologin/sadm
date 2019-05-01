# Source this file

# Errors are fatal
set -e

function this_script_must_be_run_as_root {
  if [ $(id -u) -ne 0 ]; then
      echo >&2 '[!] This script must be run as root'
      return 1
  fi
}

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
