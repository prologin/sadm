# SADM setup in containers.

## Usage

1. Configure your setup:

```bash
cat > container_setup.conf <<EOF
USE_BTRFS=false
SSH_PUB_KEY=$( readlink -f ~/.ssh/id_*.pub | head -n1 )
EOF
```

2. Setup the host:

```bash
sudo ./container_setup_host.sh
```

3. Spawn all the machines:

```bash
sudo ./container_setup_machine.sh gw
sudo ./container_setup_machine.sh monitoring
sudo ./container_setup_machine.sh web
sudo ./container_setup_machine.sh rhfs01
sudo ./container_setup_machine.sh rhfs23
sudo ./container_setup_machine.sh misc
```

## Organization

Entry points:

* `container_setup_host.sh` - Configure the host system to run containers. Run
  this first.
* `container_setup_machine.sh` - Setup a container with a given name.

Support scripts:

* `container_common.sh` - Functions and configuration common to containers

FAQ

* *Which prologin-sadm is used?* The scripts bind mounts the prologin-sadm
  which where they come from. This way you can make a change to your local
  repository and test it with the containers. This is also true for the
  prologin-sadm which is used in the exported NFS root, which is also a bind
  mount of the current prologin-sadm.
