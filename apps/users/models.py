from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager

CARGO_CHOICES = [
    ('administrador', 'Administrador'),
    ('financeiro', 'Financeiro'),
    ('usuario', 'Usuário'),
    ('corretor', 'Corretor'),
    ('produtor', 'Produtor'),
    ('auto', 'Auto'),
    ('tomador', 'Tomador'),
]

class CustomUser(AbstractUser):
    username = None

    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(unique=True)
    cargo = models.CharField(max_length=20, choices=CARGO_CHOICES, default='usuario')

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
