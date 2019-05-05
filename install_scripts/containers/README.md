SADM setup in containers.

Entry points:

* `container_setup_host.sh` - Configure the host system to run containers. Run
  this first.
* `container_setup_gw.sh` - Setup a full gw.prolo in a container
* `container_setup_rhfs.sh` - Setup a full rhfsX.prolo in a container
* `container_setup_web.sh` - Setup a full web.prolo in a container
* `container_setup_pas-r11p11.sh` - Setup a user system in a container
* `container_setup_monitoring.sh` - Setup mon.prolo in a container

Support scripts:

* `container_common_stages.sh` - Setup stages common to containers
* `container_setup_common.sh` - Functions common to containers
* `container_setup_config.sh` - Configuration variables for the container setup

FAQ

* *Which prologin-sadm is used?* The scripts copy the prologin-sadm which where
  they come from. This way you can make a change to your local repository and
  test it with the containers. This is also true for the prologin-sadm which is
  used in the exported NFS root, which is also a copy of the current
  prologin-sadm.
