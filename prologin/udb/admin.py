# Copyright (c) 2013 Pierre Bourdon <pierre.bourdon@prologin.org>
# Copyright (c) 2013 Association Prologin <info@prologin.org>
#
# Prologin-SADM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prologin-SADM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prologin-SADM.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib import admin

from prologin.udb import models


def is_root(request):
    if not request.user.is_authenticated:
        return False
    try:
        request.user.groups.get(name='root')
    except Exception:
        return False
    return True


class UIDPoolAdmin(admin.ModelAdmin):
    list_display = ('group', 'base', 'last')
    radio_fields = {'group': admin.HORIZONTAL}


class UserAdmin(admin.ModelAdmin):
    list_display = (
        'uid',
        'login',
        'group',
        'firstname',
        'lastname',
    )
    list_filter = ('group',)
    list_per_page = 250
    radio_fields = {'group': admin.HORIZONTAL}
    search_fields = (
        'uid',
        'login',
        'group',
        'firstname',
        'lastname',
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                'uid',
                'login',
            )
        else:
            return ('uid',)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            # Organizers can access the list.
            return True
        return is_root(request) or obj.group != 'root'

    def save_model(self, request, obj, form, change):
        return super().save_model(request, obj, form, change)


admin.site.register(models.UIDPool, UIDPoolAdmin)
admin.site.register(models.User, UserAdmin)
