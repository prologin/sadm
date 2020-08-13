#!/bin/bash

QUAKE_SCRIPT=$( cat <<EOF
/usr/bin/zenity --question \
    --text='Voulez-vous jouer à Quake ?' --icon-name input-gaming \
    --title 'Sondage Prologin' --ok-label Oui --cancel-label Non \
    && openarena
EOF
)

ansible user -m shell -a "/usr/bin/xrun /usr/bin/bash -c \"$QUAKE_SCRIPT\""
