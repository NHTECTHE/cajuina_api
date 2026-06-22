from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username
