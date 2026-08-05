import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestCustomUserManager:
    def test_create_user_por_email(self):
        user = User.objects.create_user(email="joao@empresa.com", password="senha123")

        assert user.email == "joao@empresa.com"
        assert user.check_password("senha123")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_sem_email_falha(self):
        with pytest.raises(ValueError, match="e-mail é obrigatório"):
            User.objects.create_user(email="", password="senha123")

    def test_create_user_normaliza_dominio(self):
        user = User.objects.create_user(email="Joao@EMPRESA.COM", password="senha123")

        assert user.email == "Joao@empresa.com"

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="admin@empresa.com", password="senha123")

        assert user.is_staff is True
        assert user.is_superuser is True

    def test_create_superuser_sem_is_staff_falha(self):
        with pytest.raises(ValueError, match="is_staff=True"):
            User.objects.create_superuser(
                email="admin@empresa.com", password="senha123", is_staff=False
            )
