import pytest
from django.contrib.auth import get_user_model

from apps.atividades.models import Atividade
from apps.atividades.services import atividade_create

User = get_user_model()


@pytest.mark.django_db
class TestAtividadeCreate:
    def test_usa_first_name_quando_existe(self):
        user = User.objects.create_user(
            email="joao@empresa.com", password="x", first_name="João"
        )

        atividade = atividade_create(
            usuario=user, acao="CRIAÇÃO", entidade="Tomador", item="ACME"
        )

        assert atividade.usuario_nome == "João"

    def test_cai_para_email_quando_nao_tem_first_name(self):
        user = User.objects.create_user(email="joao@empresa.com", password="x")

        atividade = atividade_create(
            usuario=user, acao="CRIAÇÃO", entidade="Tomador", item="ACME"
        )

        assert atividade.usuario_nome == "joao@empresa.com"

    def test_sem_usuario_registra_sistema(self):
        atividade = atividade_create(
            usuario=None, acao="CRIAÇÃO", entidade="Tomador", item="ACME"
        )

        assert atividade.usuario_nome == "Sistema"

    def test_modelo_nao_tem_mais_usuario_username(self):
        campos = {f.name for f in Atividade._meta.get_fields()}

        assert "usuario_username" not in campos
