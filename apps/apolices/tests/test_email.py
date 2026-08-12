import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.apolices.models import Apolice
from apps.atividades.models import Atividade
from apps.cotacoes.models import Cotacao
from apps.modalidades.models import Modalidade
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador

User = get_user_model()


@pytest.fixture(autouse=True)
def _limpa_throttle():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def apolice(db):
    tomador = Tomador.objects.create(
        nome="Construtora Alfa LTDA",
        cnpj="12.345.678/0001-90",
        email="contato@alfa.com.br",
    )
    modalidade = Modalidade.objects.create(nome="Seguro Garantia Judicial")
    seguradora = Seguradora.objects.create(nome="Junto Seguros", premio_minimo="100.00")
    cotacao = Cotacao.objects.create(
        tomador=tomador,
        modalidade=modalidade,
        seguradora=seguradora,
        importancia_segurada="200000.00",
        prazo_dias=30,
    )
    return Apolice.objects.create(
        cotacao=cotacao,
        seguradora=seguradora,
        numero_apolice="AP-2026-0001",
        valor_seguradora="140.00",
    )


@pytest.fixture
def client_financeiro(db):
    User.objects.create_user(
        email="fin@cajuina.com.br", password="senha123", cargo="financeiro"
    )
    client = APIClient()
    resp = client.post(
        reverse("token_obtain_pair"),
        {"email": "fin@cajuina.com.br", "password": "senha123"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.mark.django_db
class TestApoliceEnviarEmail:
    def test_cargo_usuario_nao_envia(self, apolice):
        User.objects.create_user(
            email="qualquer@gmail.com", password="senha123", cargo="usuario"
        )
        client = APIClient()
        resp = client.post(
            reverse("token_obtain_pair"),
            {"email": "qualquer@gmail.com", "password": "senha123"},
            format="json",
        )
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

        resp = client.post(
            reverse("apolice-enviar-email", args=[apolice.pk]), {}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert mail.outbox == []

    def test_destinatario_e_corpo_do_payload_sao_ignorados(
        self, apolice, client_financeiro
    ):
        resp = client_financeiro.post(
            reverse("apolice-enviar-email", args=[apolice.pk]),
            {
                "destinatario": "vitima@example.com",
                "mensagem": "Pague no PIX 12345.",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

        enviado = mail.outbox[0]
        assert enviado.to == ["contato@alfa.com.br"]
        assert "PIX 12345" not in enviado.body

    def test_corpo_e_montado_a_partir_da_apolice(self, apolice, client_financeiro):
        client_financeiro.post(
            reverse("apolice-enviar-email", args=[apolice.pk]), {}, format="json"
        )
        corpo = mail.outbox[0].body
        assert "AP-2026-0001" in corpo
        assert "Junto Seguros" in corpo
        assert "R$ 140,00" in corpo

    def test_preview_bate_com_o_enviado(self, apolice, client_financeiro):
        preview = client_financeiro.get(
            reverse("apolice-email-preview", args=[apolice.pk])
        ).data["data"]
        client_financeiro.post(
            reverse("apolice-enviar-email", args=[apolice.pk]), {}, format="json"
        )
        assert mail.outbox[0].body == preview["mensagem"]

    def test_envio_fica_registrado_em_atividades(self, apolice, client_financeiro):
        client_financeiro.post(
            reverse("apolice-enviar-email", args=[apolice.pk]), {}, format="json"
        )
        atividade = Atividade.objects.filter(acao="ENVIO", entidade="Apólice").first()
        assert atividade is not None
        assert atividade.object_id == apolice.pk

    def test_erro_de_smtp_nao_vaza_detalhe(
        self, apolice, client_financeiro, monkeypatch
    ):
        def _explode(*args, **kwargs):
            raise OSError("535 Username and Password not accepted - smtp.gmail.com")

        monkeypatch.setattr("shared.emails.send_mail", _explode)
        resp = client_financeiro.post(
            reverse("apolice-enviar-email", args=[apolice.pk]), {}, format="json"
        )
        assert resp.status_code == status.HTTP_502_BAD_GATEWAY
        assert "smtp.gmail.com" not in resp.data["detail"]
