# -*- encoding: utf-8 -*-
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


def root(request):
    if not request.user.is_authenticated():
        return False
    try:
        request.user.groups.get(name='root')
    except Exception as e:
        return False
    return True


class UserAdmin(admin.ModelAdmin):
    list_display = ('login', 'group')
    list_filter = ('group',)
    list_per_page = 250
    radio_fields = { 'group': admin.HORIZONTAL }
    search_fields = ('login', )

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True  # Let every organizer access the list
        return root(request) or obj.group != 'root'


    def save_model(self, request, obj, form, change):
        if not root(request):
            return
        return super().save_model(request, obj, form, change)


admin.site.register(models.User, UserAdmin)
