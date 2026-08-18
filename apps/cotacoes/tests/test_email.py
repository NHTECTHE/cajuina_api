from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.atividades.models import Atividade
from apps.cotacoes import services
from apps.cotacoes.models import Cotacao
from apps.emissoes.models import EmissaoSeguradora
from apps.modalidades.models import Modalidade
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador, TomadorSeguradora

User = get_user_model()


@pytest.fixture(autouse=True)
def _limpa_throttle():
    """O ScopedRateThrottle guarda o histórico no cache, que sobrevive entre
    testes: sem limpar, um teste consome a cota do seguinte."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def tomador(db):
    return Tomador.objects.create(
        nome="Construtora Alfa LTDA",
        cnpj="12.345.678/0001-90",
        email="contato@alfa.com.br",
    )


@pytest.fixture
def cotacao(db, tomador):
    modalidade = Modalidade.objects.create(nome="Seguro Garantia Judicial")
    seguradora = Seguradora.objects.create(nome="Junto Seguros", premio_minimo="100.00")
    TomadorSeguradora.objects.create(
        tomador=tomador, seguradora=seguradora, taxa="1.50"
    )
    return Cotacao.objects.create(
        tomador=tomador,
        modalidade=modalidade,
        seguradora=seguradora,
        importancia_segurada="200000.00",
        prazo_dias=30,
        edital="Edital 42/2026",
    )


def _client_com_cargo(cargo, *, email, is_superuser=False):
    user = User.objects.create_user(
        email=email, password="senha123", cargo=cargo, is_superuser=is_superuser
    )
    client = APIClient()
    resp = client.post(
        reverse("token_obtain_pair"),
        {"email": email, "password": "senha123"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client, user


@pytest.fixture
def client_financeiro(db):
    client, _ = _client_com_cargo("financeiro", email="fin@cajuina.com.br")
    return client


@pytest.mark.django_db
class TestPermissaoEnvioEmail:
    def test_cargo_usuario_nao_envia(self, cotacao):
        """`usuario` é o cargo default de quem se cadastra sozinho em
        /users/register/ (AllowAny). Liberar esse cargo devolveria o envio para
        qualquer pessoa da internet."""
        client, _ = _client_com_cargo("usuario", email="qualquer@gmail.com")
        resp = client.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert mail.outbox == []

    def test_cargo_tomador_nao_envia(self, cotacao):
        client, _ = _client_com_cargo("tomador", email="cliente@alfa.com.br")
        resp = client.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert mail.outbox == []

    def test_anonimo_nao_envia(self, cotacao):
        resp = APIClient().post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert mail.outbox == []

    def test_cargo_financeiro_envia(self, cotacao, client_financeiro):
        resp = client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 1

    def test_superusuario_envia(self, cotacao):
        """Os admins do sistema hoje têm cargo='usuario': sem essa exceção a
        funcionalidade ficaria sem ninguém."""
        client, _ = _client_com_cargo(
            "usuario", email="admin@cajuina.com", is_superuser=True
        )
        resp = client.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 1


@pytest.mark.django_db
class TestConteudoVemDoServidor:
    def test_destinatario_e_corpo_do_payload_sao_ignorados(
        self, cotacao, client_financeiro
    ):
        """Regressão: o endpoint aceitava destinatário e corpo arbitrários, o que
        permitia mandar qualquer texto para qualquer endereço com o remetente da
        corretora."""
        resp = client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]),
            {
                "destinatario": "vitima@example.com",
                "assunto": "Boleto em atraso",
                "mensagem": "Pague no PIX 12345 para evitar o cancelamento.",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

        enviado = mail.outbox[0]
        assert enviado.to == ["contato@alfa.com.br"]
        assert "vitima@example.com" not in enviado.to
        assert "PIX 12345" not in enviado.body
        assert enviado.subject == "Cotação de Seguro Garantia"

    def test_corpo_e_montado_a_partir_da_cotacao(self, cotacao, client_financeiro):
        client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        corpo = mail.outbox[0].body
        assert "Construtora Alfa LTDA" in corpo
        assert "12.345.678/0001-90" in corpo
        assert "Edital 42/2026" in corpo
        assert "Seguro Garantia Judicial" in corpo
        assert "R$ 200.000,00" in corpo
        # (200000 / 365) * 1,5% * 30 = 246,58, acima do mínimo de 100.
        assert "Junto Seguros: R$ 246,58" in corpo

    def test_observacao_entra_em_secao_identificada(self, cotacao, client_financeiro):
        client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]),
            {"observacao": "Retorno até sexta, por favor."},
            format="json",
        )
        corpo = mail.outbox[0].body
        assert "**Observações**" in corpo
        assert "Retorno até sexta, por favor." in corpo

    def test_observacao_longa_e_rejeitada(self, cotacao, client_financeiro):
        resp = client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]),
            {"observacao": "x" * 501},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert mail.outbox == []

    def test_tomador_sem_email_recebe_400(self, cotacao, client_financeiro):
        cotacao.tomador.email = ""
        cotacao.tomador.save(update_fields=["email"])
        resp = client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert mail.outbox == []

    def test_preview_mostra_o_que_sera_enviado(self, cotacao, client_financeiro):
        resp = client_financeiro.get(
            reverse("cotacao-email-preview", args=[cotacao.pk])
        )
        assert resp.status_code == status.HTTP_200_OK
        preview = resp.data["data"]
        assert preview["destinatario"] == "contato@alfa.com.br"

        client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        assert mail.outbox[0].body == preview["mensagem"]
        assert mail.outbox[0].subject == preview["assunto"]


@pytest.mark.django_db
class TestFalhaEAuditoria:
    def test_erro_de_smtp_nao_vaza_detalhe(
        self, cotacao, client_financeiro, monkeypatch
    ):
        def _explode(*args, **kwargs):
            raise OSError("535 Username and Password not accepted - smtp.gmail.com")

        monkeypatch.setattr("shared.emails.send_mail", _explode)
        resp = client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        assert resp.status_code == status.HTTP_502_BAD_GATEWAY
        assert "535" not in resp.data["detail"]
        assert "smtp.gmail.com" not in resp.data["detail"]

    def test_envio_fica_registrado_em_atividades(self, cotacao, client_financeiro):
        client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        atividade = Atividade.objects.filter(acao="ENVIO", entidade="Cotação").first()
        assert atividade is not None
        assert atividade.object_id == cotacao.pk
        assert "contato@alfa.com.br" in atividade.detalhes

    def test_falha_no_envio_nao_registra_atividade(
        self, cotacao, client_financeiro, monkeypatch
    ):
        monkeypatch.setattr(
            "shared.emails.send_mail",
            lambda *a, **k: (_ for _ in ()).throw(OSError("falhou")),
        )
        client_financeiro.post(
            reverse("cotacao-enviar-email", args=[cotacao.pk]), {}, format="json"
        )
        assert not Atividade.objects.filter(acao="ENVIO").exists()


@pytest.mark.django_db
class TestThrottle:
    def test_estoura_a_cota_e_recebe_429(self, cotacao, client_financeiro, monkeypatch):
        """DRF lê THROTTLE_RATES como atributo de classe na definição, então
        override_settings não pega: o patch é no próprio atributo."""
        from rest_framework.throttling import ScopedRateThrottle

        monkeypatch.setattr(
            ScopedRateThrottle, "THROTTLE_RATES", {"envio-email": "2/hour"}
        )
        url = reverse("cotacao-enviar-email", args=[cotacao.pk])

        assert client_financeiro.post(url, {}, format="json").status_code == 200
        assert client_financeiro.post(url, {}, format="json").status_code == 200
        terceira = client_financeiro.post(url, {}, format="json")

        assert terceira.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert len(mail.outbox) == 2


@pytest.mark.django_db
class TestPremioNoEmail:
    def test_usa_a_estimativa_enquanto_nao_cotou(self, cotacao):
        # 200.000 / 365 * 1,5% * 30 = 246,58
        corpo = services.cotacao_montar_email(cotacao=cotacao)["mensagem"]

        assert "Junto Seguros: R$ 246,58" in corpo

    def test_usa_o_premio_real_depois_de_cotar(self, cotacao):
        """Cotou de verdade: vai o número da seguradora, não a nossa conta."""
        EmissaoSeguradora.objects.create(
            cotacao=cotacao,
            seguradora=cotacao.seguradora,
            integracao="junto",
            ambiente="sandbox",
            premio_total=Decimal("777.77"),
        )

        corpo = services.cotacao_montar_email(cotacao=cotacao)["mensagem"]

        assert "Junto Seguros: R$ 777,77" in corpo
        assert "246,58" not in corpo
