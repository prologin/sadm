from oidc_provider.lib.claims import ScopeClaims
from django.core.exceptions import ObjectDoesNotExist
from .rules import WorkspaceVoucher


class ProloginSpecificClaims(ScopeClaims):
    info_workspace = (
        ('Workspace'),
        ('Web IDE related scope'),
    )

    def scope_workspace(self):
        return WorkspaceVoucher(uid=self.user.id).get_voucher()
