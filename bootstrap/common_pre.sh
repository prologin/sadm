#!/bin/bash

# Common operations for boostraping machines

echo "Updating pacman's keyring"
pacman-key --refresh-keys
