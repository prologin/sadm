#!/usr/bin/python

# Copyright: (c) 2020, Antoine Pietri (antoine.pietri@prologin.org)
# SPDX-License-Identifier: GPL3

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community',
}

DOCUMENTATION = '''
---
module: mdb

description: Manage machines in Prologin SADM's Machine Database.

options:
  hostname:
    description:
      - Hostname of the machine to add
    required: true
  state:
    description:
      - If `absent`, the machine will be deleted from `mdb`.
      - If `present`, the machine will be inserted/updated in MDB with all the
        provided information.
    default: present
    required: false
    choices: [present, absent]
  aliases:
    description:
      - List of aliases of the machine in MDB
    required: false
    default: []
  ip:
    description:
      - IP of the machine. This cannot be updated.
  mac:
    description:
      - MAC of the machine. This cannot be updated.
  rfs:
    description:
      - ID of the RFS the machine is linked to, if needed.
    required: false
  hfs:
    description:
      - ID of the HFS the machine is linked to, if needed.
    required: false
  mtype:
    description:
      - Type of machine
    choices: [user, orga, service]
    required: false
    default: service
  room:
    description:
      - Physical location of the machine
    choices: [pasteur, alt, other]
    required: false
    default: other

author:
    - Antoine Pietri (antoine.pietri1@gmail.com)
'''

EXAMPLES = '''
# Add the GW machine
- name: Add the gateway to MDB
  mdb:
    hostname: gw
    aliases: [mdb, mdbsync, ns, netboot, udb, udbsync, presencesync, ntp, sso]
    mac: 00:11:22:33:44:55
    mtype: service
    room: pasteur

# Delete a misc machine
- name: Delete the misc3 machine
  mdb:
    hostname: misc3
    state: absent
'''

import json  # noqa: E402
import shlex  # noqa: E402
from ansible.module_utils.basic import AnsibleModule  # noqa: E402
from urllib.request import urlopen  # noqa: E402


def mdb_get_machine(machine_host):
    mdb_url = "http://mdb/call/query"
    with urlopen(mdb_url) as f:
        mdb_res = f.read().decode()
        mdb_status = json.loads(mdb_res)['data']
        machine = next(
            (m for m in mdb_status if m['hostname'] == machine_host), None
        )
        if machine:
            machine = {**machine, 'state': 'present'}
        else:
            machine = {'hostname': machine_host, 'state': 'absent'}
    return machine


def run_module():
    module_args = dict(
        state=dict(
            type='str',
            choices=('present', 'absent'),
            required=False,
            default='present',
        ),
        manage_command=dict(
            type='str',
            required=False,
            default=(
                '/opt/prologin/venv/bin/python /opt/prologin/mdb/manage.py'
            ),
        ),
        # Machine attributes
        hostname=dict(type='str', required=True),
        aliases=dict(type='list', elements='str', required=False),
        mac=dict(type='str', required=False),
        ip=dict(type='str', required=False),
        rfs=dict(type='int', required=False),
        hfs=dict(type='int', required=False),
        mtype=dict(
            type='str', choices=('user', 'orga', 'service'), required=False,
        ),
        room=dict(
            type='str', choices=('pasteur', 'alt', 'other'), required=False,
        ),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    update_fields = ('aliases', 'rfs', 'hfs', 'mtype', 'room')
    create_fields = ('ip', 'mac', 'hostname')
    fields = update_fields + create_fields + ('state',)

    machine_host = module.params['hostname']
    old_machine = mdb_get_machine(machine_host)

    new_machine = {
        k: (','.join(v) if isinstance(v, list) else v)
        for k, v in module.params.items()
        if k in fields
        if v is not None
    }

    if old_machine['state'] == 'present':
        # In update mode, check that all the read-only fields match
        for f in create_fields:
            if f in new_machine and old_machine[f] != new_machine[f]:
                msg = (
                    "Field {} does not match for machine {} and cannot be "
                    "updated (old={}, new={}).".format(
                        f, machine_host, old_machine[f], new_machine[f]
                    )
                )
                module.fail_json(msg=msg)
    else:
        if new_machine['state'] == 'present':
            # In create mode, fill all the empty fields with default values
            new_machine.setdefault('rfs', 0)
            new_machine.setdefault('hfs', 0)
            new_machine.setdefault('aliases', '')
            new_machine.setdefault('mtype', 'service')
            new_machine.setdefault('room', 'other')

            # MAC needs to be present
            if not new_machine.get('mac'):
                msg = "Field mac not present, cannot create machine {}.".format(
                    machine_host
                )
                module.fail_json(msg=msg)

    result = dict(changed=False, diff=dict(before={}, after={}))

    # Diff
    result['diff']['before'] = {
        k: v for k, v in old_machine.items() if k in new_machine
    }
    result['diff']['after'] = new_machine
    if result['diff']['before'] != result['diff']['after']:
        result['changed'] = True

    if module.check_mode:
        module.exit_json(**result)

    command = list(shlex.split(module.params['manage_command']))
    if new_machine['state'] == 'present':
        command += ['addmachine', '--update']
        for k, v in new_machine.items():
            if k != 'state':
                command += ['--{}'.format(k), str(v)]
    elif new_machine['state'] == 'absent':
        command += ['delmachine', machine_host]

    if result['changed']:
        rc, out, err = module.run_command(command)
        if rc != 0:
            msg = ''
            if out:
                msg += "stdout: %s" % (out,)
            if err:
                msg += "\n:stderr: %s" % (err,)
            module.fail_json(cmd=command, msg=msg, **result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
