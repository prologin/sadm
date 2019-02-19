from django.conf import settings
from django.db import models


class OAuthToken(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL, unique=True,
        on_delete=models.CASCADE)
    token = models.CharField(max_length=64, null=True, default=None)
    expirancy = models.DateTimeField(null=True, default=None)

