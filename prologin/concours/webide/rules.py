from . import models
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model

import requests

class WorkspaceVoucher:
    def workspace_populate(self):
        try:
            self.workspace = models.UserMachine.objects.get(user=self.uid)
        except ObjectDoesNotExist:
            machine = self.machine_attribution()
            if not machine:
                self.workspace = None
                return

            self.workspace = models.UserMachine(user=get_user_model().objects.get(pk=self.uid), workspace=machine)
            self.workspace.save()
            self.call_podman_api()

    def call_podman_api(self):
        machine = f"http://{self.workspace.workspace.host}.{self.workspace.workspace.room}.sm.cri.epita.net:{self.workspace.workspace.port}/start"
        requests.post(machine, data={ "uid": self.dic['ws_uid'] })

    def machine_attribution(self):
        free_machines = models.MachineTheia.objects.filter(usermachine=None)

        if not free_machines:
            return None

        return free_machines[0]

    def __init__(self, uid):
        self.dic = {}
        self.uid = uid
        self.dic['ws_uid'] = str(self.uid)
        self.workspace_populate()
        self.dic['ws_host'] = (
            None if not self.workspace else self.workspace.workspace.host
        )
        self.dic['ws_port'] = (
            None if not self.workspace else self.workspace.workspace.port
        )
        self.dic['ws_room'] = (
            None if not self.workspace else self.workspace.workspace.room
        )

    def get_voucher(self):
        print(self.dic)
        return self.dic
