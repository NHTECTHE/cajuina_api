import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

User = get_user_model()


@pytest.mark.django_db
class TestCreateDefaultUser:
    def test_cria_superusuario_por_email(self):
        call_command("create_default_user")

        user = User.objects.get(email="admin@example.com")
        assert user.is_superuser is True
        assert user.check_password("senha")

    def test_e_idempotente(self):
        call_command("create_default_user")
        call_command("create_default_user")

        assert User.objects.filter(email="admin@example.com").count() == 1
