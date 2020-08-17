#!/bin/bash

ansible user -m shell -a "/usr/bin/xrun /usr/bin/zenity --info --text='Allez manger !' --icon-name face-cool"
