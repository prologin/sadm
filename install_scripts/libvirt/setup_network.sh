#!/bin/bash
set -e

# Internal SADM lan
sudo ip link add br-prolo type bridge
sudo ip link set br-prolo up
