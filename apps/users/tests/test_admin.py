import pytest
from django.contrib import admin
from django.core import checks

from apps.users.models import CustomUser


@pytest.mark.django_db
def test_admin_de_usuario_nao_referencia_username():
    admin_class = admin.site._registry[CustomUser]
    erros = admin_class.check()

    assert erros == [], f"Admin com erros de configuração: {erros}"


@pytest.mark.django_db
def test_system_checks_sem_erros():
    erros = checks.run_checks()
    graves = [e for e in erros if e.level >= checks.ERROR]

    assert graves == [], f"System checks falharam: {graves}"
