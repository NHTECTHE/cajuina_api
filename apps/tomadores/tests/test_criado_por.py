import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.tomadores.models import Tomador

User = get_user_model()


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        email="tester@empresa.com", password="senha123", first_name="Tester"
    )


@pytest.fixture
def auth_client(usuario):
    client = APIClient()
    resp = client.post(
        reverse("token_obtain_pair"),
        {"email": "tester@empresa.com", "password": "senha123"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.mark.django_db
class TestTomadorCriadoPor:
    def test_create_grava_o_usuario_autenticado(self, auth_client, usuario):
        resp = auth_client.post(
            reverse("tomador-list-create"),
            {"cnpj": "11.222.333/0001-44", "nome": "ACME LTDA"},
            format="json",
        )

        assert resp.status_code == 201
        tomador = Tomador.objects.get(cnpj="11.222.333/0001-44")
        assert tomador.criado_por_id == usuario.id

    def test_serializer_expoe_criado_por_nome(self, auth_client, usuario):
        resp = auth_client.post(
            reverse("tomador-list-create"),
            {"cnpj": "11.222.333/0001-44", "nome": "ACME LTDA"},
            format="json",
        )

        assert resp.data["data"]["criado_por_nome"] == "Tester"

    def test_tomador_antigo_fica_com_criado_por_nulo(self, auth_client):
        tomador = Tomador.objects.create(cnpj="99.888.777/0001-11", nome="ANTIGA LTDA")

        resp = auth_client.get(reverse("tomador-detail", args=[tomador.id]))

        assert resp.status_code == 200
        assert resp.data["data"]["criado_por_nome"] is None

    def test_criado_por_e_read_only(self, auth_client, usuario):
        outro = User.objects.create_user(email="outro@empresa.com", password="x")

        resp = auth_client.post(
            reverse("tomador-list-create"),
            {"cnpj": "11.222.333/0001-44", "nome": "ACME LTDA", "criado_por": outro.id},
            format="json",
        )

        assert resp.status_code == 201
        tomador = Tomador.objects.get(cnpj="11.222.333/0001-44")
        assert tomador.criado_por_id == usuario.id
