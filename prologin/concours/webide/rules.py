from . import models
from django.core.exceptions import ObjectDoesNotExist


class WorkspaceVoucher:
    def workspace_populate(self):
        try:
            self.workspace = models.UserMachine.objects.get(user=self.uid)
        except ObjectDoesNotExist:
            self.workspace = models.UserMachine()
            self.workspace.uid = self.uid
            self.workspace.workspace = 0
            self.workspace.save()

    def call_podman_api(self):
        pass

    def machine_attribution(self):
        free_machines = models.MachineTheia.objects.filter(usermachine=None)
        self.dic['ws_host'] = (
            None if not free_machines else free_machines[0].host
        )
        self.dic['ws_port'] = (
            None if not free_machines else free_machines[0].port
        )
        self.dic['ws_room'] = (
            None if not free_machines else free_machines[0].room
        )

        if free_machines:
            self.call_podman_api()

    def __init__(self, uid):
        self.dic = {}
        self.uid = uid
        self.dic['ws_uid'] = str(self.uid)
        self.workspace_populate()
        self.machine_attribution()

    def get_voucher(self):
        print(self.dic)
        return self.dic
