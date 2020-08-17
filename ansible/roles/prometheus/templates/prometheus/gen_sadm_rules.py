#!/usr/bin/env python3
import yaml


def main():
    # Input
    systemd_units_running = {
        "gw.prolo": [
            "postgresql.service",
            "mdb.service",
            "nginx.service",
            "mdbsync.service",
            "mdbdns.service",
            "named.service",
            "mdbdhcp.service",
            "dhcpd4.service",
            "netboot.service",
            "tftpd.socket",
            "udb.service",
            "udbsync.service",
            "udbsync_django@mdb.service",
            "udbsync_django@udb.service",
            "udbsync_rootssh.service",
            "presencesync.service",
            "presencesync_sso.service",
            "firewall.service",
            "presencesync_firewall.service",
        ],
    }
    systemd_units_running.update({
        f"rhfs{rhfs}{rhfs + 1}.prolo": [
            "udbsync_passwd.service",
            "udbsync_passwd_nfsroot.service",
            "udbsync_rootssh.service",
            "rpcbind.service",
            "nfs-server.service",
            "rootssh.path",
        ]
        for rhfs in range(0, 9, 2)
    })

    # Create file structure
    root = {'groups': []}
    groups = root['groups']
    group = {'name': 'sadm.rules', 'rules': []}
    groups.append(group)
    rules = group['rules']

    # Add alerts
    for instance, services in systemd_units_running.items():
        for service in services:
            rule = {
                'alert': f'{instance}_{service}_NotActive',
                'expr':
                f'node_systemd_unit_state{{instance="{instance}", name="{service}", state="active"}} == 0',
                'for': '30s',
                'annotations': {
                    'summary': f'{service} is not active on {instance}',
                    'description': f'ssh {instance} journalctl -eu {service}',
                },
            }
            rules.append(rule)

    # Output
    with open("sadm.rules.yml", "w") as fd:
        yaml.dump(root, fd, width=120)


if __name__ == "__main__":
    main()
