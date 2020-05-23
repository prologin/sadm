This is a work-in-progress, the intent is to completely replace the sadm
install scripts and a large part of the container setup scripts.

HOWTO:

1. Follow https://prologin-sadm.readthedocs.io/containers.html until it asks
   you to run ./container_setup_host.sh. This will create an arch_linux_base
   image in /var/lib/machines that you will use to spawn new machines.

2. Make sure to have /root/.ssh/id_*.pub == your public key, to be able to ssh
   to the machines afterwards.

3. Spawn all the required machines (as root)

./spawn_prolo_test_machine.sh gw
./spawn_prolo_test_machine.sh monitoring
./spawn_prolo_test_machine.sh web
./spawn_prolo_test_machine.sh rhfs01
./spawn_prolo_test_machine.sh rhfs23
./spawn_prolo_test_machine.sh misc

4. Run ansible

ansible-playbook playbook-all-sadm.yml
