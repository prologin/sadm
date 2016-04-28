Arch Linux repository
=====================

Prologin has setup an Arch Linux package repository to ease of use of
custom packages and AUR content.

Usage
-----

Add the following section to the ``/etc/pacman.conf`` file:

    [prologin]
    Server = https://repo.prologin.org/

Then, trust the repository signing keys:

    # wget https://repo.prologin.org/prologin.pub
    # pacman-key --add prologin.pub
    # pacman-key --lsign-key prologin

Finally, test the repository:

    pacman -Sy

You should see "prologin" in the list of synchronized package databases.

Uploading packages to the reposityory
-------------------------------------

Only the owner of the repository's private key and ssh access to
repo@prologin.org can upload packages.

To import the private key to your keystore:

    $ ssh repo@prologin.org 'gpg --export-secret-keys --armor F4592F5F00D9EA8279AE25190312438E8809C743' | gpg --import
    $ gpg --edit-key F4592F5F00D9EA8279AE25190312438E8809C743

Trust fully the key.

Then, build the package you want to upload locally using ``makepkg``. Once the
package is built, use the ``pkg/upload2repo.sh`` to sign it, update the database
and upload it.

Example usage:

    $ cd quake3-pak0.pk3
    $ makepkg
    $ ~/sadm/pkg/upload2repo.sh quake3-pak0.pk3-1-1-x86_64.pkg.tar.xz

You can then install the package like any other:

    # pacman -Sy quake3-pak0.pk3
    $ quake3

Enjoy!

More information
----------------

The repository is stored in ``rosa:~repo/www``

Troubleshooting
---------------

Invalid signature of a database or a package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This should not happen. If it does, find the broken signature and re-sign the
file using ``gpg --sign``. You must also investigate why an invalid signature
was generated.
