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
from prologin.mdb import models


class IPPoolAdmin(admin.ModelAdmin):
    list_display = ('mtype', 'network', 'last')
    radio_fields = { 'mtype': admin.HORIZONTAL }


class MachineAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'aliases', 'ip', 'mtype', 'room')
    list_filter = ('mtype', 'room')
    list_per_page = 250
    radio_fields = { 'mtype': admin.HORIZONTAL, 'room': admin.HORIZONTAL }
    search_fields = ('hostname', 'aliases', 'ip', 'mac')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['ip', 'mac', 'hostname']
        else:
            return ['ip']


class VolatileSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value_bool', 'value_str', 'value_int')
    search_fields = ('key', 'value_str')


admin.site.register(models.IPPool, IPPoolAdmin)
admin.site.register(models.Machine, MachineAdmin)
admin.site.register(models.VolatileSetting, VolatileSettingAdmin)
