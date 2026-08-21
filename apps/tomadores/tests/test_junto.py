import time
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.atividades.models import Atividade
from apps.emissoes.conectores.base import TaxaTomador, TomadorSeguradoraInfo
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador, TomadorSeguradora

# Fixtures localizados para tornar o arquivo de testes independente


@pytest.fixture
def client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(email="tester@empresa.com", password="senha123")


@pytest.fixture
def auth_client(client, user):
    from django.urls import reverse

    resp = client.post(
        reverse("token_obtain_pair"),
        {"email": "tester@empresa.com", "password": "senha123"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def tomador(db):
    return Tomador.objects.create(cnpj="12.345.678/0001-90", nome="Construtora Teste")


@pytest.fixture
def junto(db):
    return Seguradora.objects.create(
        nome="Junto Seguros",
        integracao="junto",
        api_ambiente="sandbox",
        api_client_id="id-teste",
        api_client_secret="segredo-teste",
        premio_minimo="140.00",
        vencimento_dias=20,
    )


@pytest.fixture
def sem_integracao(db):
    return Seguradora.objects.create(
        nome="Pottencial", premio_minimo="100.00", vencimento_dias=20
    )


def _apontar_para_porta_morta(monkeypatch):
    """Faz o conector real apontar para uma porta fechada.

    Exercita o caminho de rede de verdade (httpx levantando ConnectError), que é
    o cenário em que a versão antiga devolvia a taxa fabricada.
    """
    monkeypatch.setattr(
        "apps.emissoes.conectores.junto.BASE_URLS",
        {"sandbox": "http://127.0.0.1:9", "producao": "http://127.0.0.1:9"},
    )
    from apps.emissoes.conectores.junto import limpar_cache_token

    limpar_cache_token()


def _mock_client(monkeypatch, fake):
    """Troca o conector que as views resolvem via `get_conector`.

    As views importam `get_conector` no topo do módulo, então o patch precisa ser
    no nome que elas guardam — não no módulo do registry.
    """
    monkeypatch.setattr("apps.tomadores.api.v1.views.get_conector", lambda s, **k: fake())


@pytest.mark.django_db
class TestJuntoIntegration:
    def test_verificar_found_sets_cadastro_ok(self, auth_client, tomador, junto, monkeypatch):
        # Mockar o client via monkeypatch na importação usada pelos serviços
        class FakeClient:
            def consultar_tomador(self, *, cnpj):
                return TomadorSeguradoraInfo(
                    cnpj="12345678000190", nome="Construtora Teste",
                    cidade="FORTALEZA", uf="CE",
                    valido_ate=timezone.now().date() + timedelta(days=30),
                )

        _mock_client(monkeypatch, FakeClient)

        url = reverse("tomador-seguradora-junto-verificar", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["status"] == TomadorSeguradora.Status.CADASTRO_OK

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert vinculo.status == TomadorSeguradora.Status.CADASTRO_OK
        assert vinculo.junto_data_ultima_verificacao is not None
        assert vinculo.junto_validade_cadastro is not None

    def test_verificar_not_found_keeps_sem_cadastro(self, auth_client, tomador, junto, monkeypatch):
        class FakeClient:
            def consultar_tomador(self, *, cnpj):
                return None

        _mock_client(monkeypatch, FakeClient)

        url = reverse("tomador-seguradora-junto-verificar", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["status"] == TomadorSeguradora.Status.SEM_CADASTRO

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert vinculo.status == TomadorSeguradora.Status.SEM_CADASTRO

    def test_solicitar_creates_activity_and_prevents_duplicate(self, auth_client, tomador, junto, monkeypatch):
        class FakeClient:
            def cadastrar_tomador(self, *, cnpj):
                return None

            def consultar_tomador(self, *, cnpj):
                return None

        _mock_client(monkeypatch, FakeClient)

        url = reverse("tomador-seguradora-junto-solicitar", args=[tomador.pk, junto.pk])
        resp1 = auth_client.post(url, {}, format="json")
        assert resp1.status_code == status.HTTP_202_ACCEPTED
        assert resp1.data["data"]["pendente"] is True

        atividades = Atividade.objects.filter(
            entidade="Tomador", object_id=tomador.id, acao="ATUALIZAÇÃO"
        )
        assert atividades.count() == 1

        # Segunda solicitação dentro da janela é recusada explicitamente.
        resp2 = auth_client.post(url, {}, format="json")
        assert resp2.status_code == status.HTTP_409_CONFLICT
        assert atividades.count() == 1

    def test_solicitar_volta_a_funcionar_depois_da_janela(
        self, auth_client, tomador, junto, monkeypatch
    ):
        """A antiduplicidade é uma janela, não uma trava permanente.

        Regressão do PR #27: o guard original era `.exists()` sem recorte de
        tempo, então a primeira tentativa bloqueava o tomador para sempre.
        """

        class FakeClient:
            def cadastrar_tomador(self, *, cnpj):
                return None

        _mock_client(monkeypatch, FakeClient)

        url = reverse("tomador-seguradora-junto-solicitar", args=[tomador.pk, junto.pk])
        assert auth_client.post(url, {}, format="json").status_code == 202
        assert auth_client.post(url, {}, format="json").status_code == 409

        # Envelhece a atividade para além da janela.
        Atividade.objects.filter(entidade="Tomador", object_id=tomador.id).update(
            criado_em=timezone.now() - timedelta(minutes=6)
        )
        assert auth_client.post(url, {}, format="json").status_code == 202

    def test_solicitar_nao_bloqueia_o_worker(
        self, auth_client, tomador, junto, monkeypatch
    ):
        """Regressão: a versão original fazia 4x `time.sleep(1)` dentro do request."""

        class FakeClient:
            def cadastrar_tomador(self, *, cnpj):
                return None

        _mock_client(monkeypatch, FakeClient)

        url = reverse("tomador-seguradora-junto-solicitar", args=[tomador.pk, junto.pk])
        inicio = time.monotonic()
        auth_client.post(url, {}, format="json")
        assert time.monotonic() - inicio < 1.0

    def test_consultar_taxa_read_only_and_records_activity(self, auth_client, tomador, junto, monkeypatch):
        from decimal import Decimal

        class FakeClient:
            def consultar_taxa_tomador(self, *, cnpj):
                return TaxaTomador(
                    taxa=Decimal("1.2478"), modalidade_id=99,
                    modalidade_descricao="Licitante",
                    limite_disponivel=Decimal("500000.00"),
                )

        _mock_client(monkeypatch, FakeClient)

        url = reverse("tomador-seguradora-junto-taxa", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["taxa"] == "1.2478"
        assert data["modalidade_id"] == "99"
        assert data["modalidade_descricao"] == "Licitante"

        # É endpoint de leitura: não grava taxa e não cria vínculo por efeito colateral.
        assert not TomadorSeguradora.objects.filter(
            tomador=tomador, seguradora=junto
        ).exists()

        # A consulta fica no histórico do tomador, que é o que a tela exibe.
        atividades = Atividade.objects.filter(
            entidade="Tomador", object_id=tomador.id, acao="ATUALIZAÇÃO"
        )
        assert atividades.count() == 1
        assert "Taxa 1.2478%" in atividades.first().detalhes
        assert "modalidade 99 (Licitante)" in atividades.first().detalhes

    def test_taxa_6_casas_e_origem_salvas(self, auth_client, tomador, junto):
        from decimal import Decimal

        url = reverse("tomador-seguradora-list", args=[tomador.pk])
        payload = {
            "itens": [
                {
                    "seguradora": junto.pk,
                    "status": "sem_cadastro",
                    "taxa": "1.247800",
                    "taxa_origem": "junto",
                    "taxa_junto_modalidade_id": "99",
                    "taxa_junto_modalidade_descricao": "Licitante",
                    "taxa_data_atualizacao": "2026-08-19T18:00:00Z",
                    "premio_minimo": None,
                    "dias_vencimento": None,
                }
            ]
        }
        resp = auth_client.put(url, payload, format="json")
        assert resp.status_code == status.HTTP_200_OK

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert vinculo.taxa == Decimal("1.2478")
        assert vinculo.taxa_origem == "junto"
        assert vinculo.taxa_junto_modalidade_id == "99"

    def test_edicao_manual_limpa_origem(self, auth_client, tomador, junto):
        from decimal import Decimal

        url = reverse("tomador-seguradora-list", args=[tomador.pk])
        payload = {
            "itens": [
                {
                    "seguradora": junto.pk,
                    "status": "sem_cadastro",
                    "taxa": "1.50",
                    "taxa_origem": "",
                    "taxa_junto_modalidade_id": "",
                    "taxa_junto_modalidade_descricao": "",
                    "taxa_data_atualizacao": None,
                    "premio_minimo": None,
                    "dias_vencimento": None,
                }
            ]
        }
        resp = auth_client.put(url, payload, format="json")
        assert resp.status_code == status.HTTP_200_OK

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert vinculo.taxa == Decimal("1.5")
        assert vinculo.taxa_origem == ""
        assert vinculo.taxa_junto_modalidade_id == ""

    def test_taxa_com_mais_de_6_casas_retorna_erro(self, auth_client, tomador, junto):
        url = reverse("tomador-seguradora-list", args=[tomador.pk])
        payload = {
            "itens": [
                {
                    "seguradora": junto.pk,
                    "status": "sem_cadastro",
                    "taxa": "1.1234567",
                    "premio_minimo": None,
                    "dias_vencimento": None,
                }
            ]
        }
        resp = auth_client.put(url, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_taxa_maior_ou_igual_1000_retorna_erro(self, auth_client, tomador, junto):
        url = reverse("tomador-seguradora-list", args=[tomador.pk])
        payload = {
            "itens": [
                {
                    "seguradora": junto.pk,
                    "status": "sem_cadastro",
                    "taxa": "1000.00",
                    "premio_minimo": None,
                    "dias_vencimento": None,
                }
            ]
        }
        resp = auth_client.put(url, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestJuntoFalhaDeIntegracao:
    """Regressões dos achados críticos do PR #27.

    O ponto comum: uma Junto que não responde não pode virar dado de negócio.
    """

    def test_api_fora_do_ar_nao_inventa_taxa(
        self, auth_client, tomador, junto, monkeypatch
    ):
        """O client original devolvia 200 com taxa fixa 1.2478 e origem "junto".

        Um corretor salvava esse número achando que veio da seguradora, e ele
        virava o prêmio real das cotações daquele par.
        """
        _apontar_para_porta_morta(monkeypatch)

        url = reverse("tomador-seguradora-junto-taxa", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_502_BAD_GATEWAY
        assert "taxa" not in resp.data["data"]
        # O signal de criação do Tomador já grava uma "CRIAÇÃO"; o que não pode
        # existir é o registro de consulta de taxa.
        assert not Atividade.objects.filter(
            entidade="Tomador", acao="ATUALIZAÇÃO"
        ).exists()

    def test_api_fora_do_ar_nao_vira_sem_cadastro(
        self, auth_client, tomador, junto, monkeypatch
    ):
        """Falha de infra não pode ser lida como "tomador não tem cadastro".

        Era o que acontecia: a tela afirmava que o tomador não existia na Junto e
        oferecia cadastrar — podendo disparar cadastro duplicado de verdade.
        """
        _apontar_para_porta_morta(monkeypatch)

        url = reverse("tomador-seguradora-junto-verificar", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_502_BAD_GATEWAY
        assert not TomadorSeguradora.objects.filter(
            tomador=tomador, seguradora=junto
        ).exists()

    def test_credencial_recusada_vira_502_e_nao_sem_cadastro(
        self, auth_client, tomador, junto, monkeypatch
    ):
        from apps.emissoes.conectores.base import SeguradoraIndisponivel

        class FakeClient:
            def consultar_tomador(self, *, cnpj):
                raise SeguradoraIndisponivel("Falha de autenticação na Junto.")

        _mock_client(monkeypatch, FakeClient)

        url = reverse("tomador-seguradora-junto-verificar", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_502_BAD_GATEWAY
        assert "autenticação" in resp.data["data"]["error"]

    def test_recusa_de_negocio_continua_400(
        self, auth_client, tomador, junto, monkeypatch
    ):
        from apps.emissoes.conectores.base import ErroValidacaoSeguradora

        class FakeClient:
            def consultar_taxa_tomador(self, *, cnpj):
                raise ErroValidacaoSeguradora("Tomador sem modalidade na Junto.")

        _mock_client(monkeypatch, FakeClient)

        url = reverse("tomador-seguradora-junto-taxa", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_seguradora_sem_integracao_da_400_sem_tocar_a_rede(
        self, auth_client, tomador, sem_integracao, monkeypatch
    ):
        _apontar_para_porta_morta(monkeypatch)

        for rota in (
            "tomador-seguradora-junto-verificar",
            "tomador-seguradora-junto-solicitar",
            "tomador-seguradora-junto-taxa",
        ):
            url = reverse(rota, args=[tomador.pk, sem_integracao.pk])
            resp = auth_client.post(url, {}, format="json")
            assert resp.status_code == status.HTTP_400_BAD_REQUEST, rota
            assert "integrada" in resp.data["data"]["error"]

    def test_cnpj_invalido_nao_chama_a_junto(self, auth_client, junto, db, monkeypatch):
        _apontar_para_porta_morta(monkeypatch)
        tomador = Tomador.objects.create(cnpj="123", nome="CNPJ Quebrado")

        url = reverse("tomador-seguradora-junto-verificar", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["data"]["error"] == "CNPJ inválido."

    def test_cadastro_vencido_conta_como_sem_cadastro(
        self, auth_client, tomador, junto, monkeypatch
    ):
        class FakeClient:
            def consultar_tomador(self, *, cnpj):
                return TomadorSeguradoraInfo(
                    cnpj="12345678000190", nome="X", cidade="FORTALEZA", uf="CE",
                    valido_ate=timezone.now().date() - timedelta(days=1),
                )

        _mock_client(monkeypatch, FakeClient)

        url = reverse("tomador-seguradora-junto-verificar", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["status"] == TomadorSeguradora.Status.SEM_CADASTRO
