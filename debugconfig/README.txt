Because most Prologin services don't define a default configuration yet, we
need this directory of default options to be able to run the code locally.

Use it like this:

    export CFG_DIR=$( readlink -f debugconfig/ )

This is a legacy directory that will disappear once
https://github.com/prologin/sadm/issues/186 is solved.
