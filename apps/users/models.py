from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    # Você pode adicionar campos personalizados aqui futuramente
    # ex: cpf = models.CharField(max_length=14, unique=True)
    pass
