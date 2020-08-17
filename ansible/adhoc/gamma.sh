#!/bin/bash

if [ $# -lt 1 ]; then
    echo 'Usage: $0 [red|reset]'
    exit 1
fi

gamma_value="1:1:1"
if [ $1 == "red" ]; then
    gamma_value="1:.5:.5"
fi

ansible user -m shell -a "/usr/bin/xrun /usr/bin/xrandr --output DP1 --gamma $gamma_value"
