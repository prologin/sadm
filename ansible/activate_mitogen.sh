#!/bin/bash

# Run `source activate_mitogen.sh` to download mitogen and add the ansible
# mitogen strategy to your environment variables.

ver=mitogen-0.2.9

if ! test -f .mitogen/$ver/ansible_mitogen/plugins/strategy/__init__.py; then
    mkdir -p .mitogen
    wget -q -c https://networkgenomics.com/try/$ver.tar.gz -P .mitogen
    tar -C .mitogen -xf .mitogen/$ver.tar.gz
fi

export ANSIBLE_STRATEGY=mitogen_linear
export ANSIBLE_STRATEGY_PLUGINS=$( readlink -f .mitogen/$ver/ansible_mitogen/plugins/strategy )
