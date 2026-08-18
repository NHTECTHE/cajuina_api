"""O prêmio que a tela de proposta mostra sai da seguradora, quando existe."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.cotacoes.models import Cotacao
from apps.emissoes.models import EmissaoSeguradora
from apps.modalidades.models import Modalidade
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador

User = get_user_model()


@pytest.fixture
def cliente(db):
    usuario = User.objects.create_user(email="op@cajuina.com.br", password="x")
    api = APIClient()
    api.force_authenticate(user=usuario)
    return api


@pytest.fixture
def cotacao(db):
    tomador = Tomador.objects.create(
        nome="Construtora Alfa LTDA", cnpj="12.345.678/0001-90"
    )
    return Cotacao.objects.create(
        tomador=tomador,
        modalidade=Modalidade.objects.create(nome="Seguro Garantia Judicial"),
        seguradora=Seguradora.objects.create(
            nome="Junto Seguros", premio_minimo="100.00"
        ),
        importancia_segurada="200000.00",
        prazo_dias=30,
        edital="Edital 42/2026",
    )


@pytest.mark.django_db
class TestPremioSeguradora:
    def test_null_quando_a_escolhida_nao_foi_cotada(self, cliente, cotacao):
        resposta = cliente.get(reverse("cotacao-detail", args=[cotacao.pk]))

        assert resposta.data["data"]["premio_seguradora"] is None

    def test_traz_o_premio_real_da_escolhida(self, cliente, cotacao):
        EmissaoSeguradora.objects.create(
            cotacao=cotacao,
            seguradora=cotacao.seguradora,
            integracao="junto",
            ambiente="sandbox",
            premio_total=Decimal("777.77"),
        )

        resposta = cliente.get(reverse("cotacao-detail", args=[cotacao.pk]))

        assert resposta.data["data"]["premio_seguradora"] == "777.77"

    def test_ignora_emissao_de_seguradora_nao_escolhida(self, cliente, cotacao):
        """Cotou em duas, escolheu uma: vale a escolhida."""
        outra = Seguradora.objects.create(
            nome="Pottencial Seguradora", premio_minimo="100.00"
        )
        EmissaoSeguradora.objects.create(
            cotacao=cotacao,
            seguradora=outra,
            integracao="",
            ambiente="sandbox",
            premio_total=Decimal("999.99"),
        )

        resposta = cliente.get(reverse("cotacao-detail", args=[cotacao.pk]))

        assert resposta.data["data"]["premio_seguradora"] is None
