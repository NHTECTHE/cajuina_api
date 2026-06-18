import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    activation_token = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)

    def __str__(self):
        return self.username

