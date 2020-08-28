from django.db import models
from django.contrib.auth import get_user_model


class MachineTheia(models.Model):
    host = models.CharField(max_length=10)
    room = models.CharField(max_length=20)
    port = models.IntegerField()

    def __str__(self):
        return f'{self.host}.{self.room}.sm.cri.epita.net:{self.port}'

    class Meta:
        unique_together = ('host', 'room', 'port')


class UserMachine(models.Model):
    user = models.OneToOneField(
        to=get_user_model(), primary_key=True, on_delete=models.CASCADE
    )
    workspace = models.OneToOneField(
        to='MachineTheia', on_delete=models.CASCADE
    )
