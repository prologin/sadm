from django.contrib import admin
from . import models


@admin.register(models.MachineTheia)
class MachineTheiaAdmin(admin.ModelAdmin):
    list_display = ('host', 'room', 'port')
    search_fields = ('host', 'room', 'port')


@admin.register(models.UserMachine)
class UserMachineAdmin(admin.ModelAdmin):
    list_display = ('user', 'workspace')
    list_filter = ('workspace',)
    search_fields = ('user', 'workspace')
