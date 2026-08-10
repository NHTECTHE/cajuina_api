import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.apolices.models import Apolice
from apps.atividades.models import Atividade
from apps.cotacoes.models import Cotacao
from apps.modalidades.models import Modalidade
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador, TomadorSeguradora

User = get_user_model()

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="tester@empresa.com", password="senha123")


@pytest.fixture
def auth_client(client, user):
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
def modalidade(db):
    return Modalidade.objects.create(nome="Garantia")


@pytest.fixture
def seguradora(db):
    return Seguradora.objects.create(nome="Alfa Seguros", premio_minimo="500.00")


def emitir_apolice(*, tomador, modalidade, seguradora, valor, numero):
    cotacao = Cotacao.objects.create(
        tomador=tomador, modalidade=modalidade, status=Cotacao.STATUS_EMITIDO
    )
    return Apolice.objects.create(
        cotacao=cotacao,
        seguradora=seguradora,
        numero_apolice=numero,
        valor_seguradora=valor,
    )


# ─── Prêmio acumulado ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTomadorPremioAcumulado:
    def url(self, tomador):
        return reverse("tomador-premio-acumulado", args=[tomador.pk])

    def test_exige_autenticacao(self, client, tomador):
        resp = client.get(self.url(tomador))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_tomador_inexistente_retorna_404(self, auth_client):
        resp = auth_client.get(reverse("tomador-premio-acumulado", args=[9999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_soma_apolices_do_tomador(
        self, auth_client, tomador, modalidade, seguradora
    ):
        emitir_apolice(
            tomador=tomador,
            modalidade=modalidade,
            seguradora=seguradora,
            valor="100.00",
            numero="A1",
        )
        emitir_apolice(
            tomador=tomador,
            modalidade=modalidade,
            seguradora=seguradora,
            valor="250.50",
            numero="A2",
        )

        resp = auth_client.get(self.url(tomador))
        data = resp.data["data"]

        assert resp.status_code == status.HTTP_200_OK
        assert data["premio_total"] == "350.50"
        assert data["seguradoras"] == [
            {"id": seguradora.id, "nome": "Alfa Seguros", "total": "350.50"}
        ]

    def test_nao_soma_apolice_de_outro_tomador(
        self, auth_client, tomador, modalidade, seguradora
    ):
        outro = Tomador.objects.create(cnpj="99.888.777/0001-66", nome="Outra Empresa")
        emitir_apolice(
            tomador=outro,
            modalidade=modalidade,
            seguradora=seguradora,
            valor="900.00",
            numero="B1",
        )

        resp = auth_client.get(self.url(tomador))
        assert resp.data["data"]["premio_total"] == "0.00"

    def test_seguradora_sem_apolice_vem_zerada(self, auth_client, tomador, seguradora):
        resp = auth_client.get(self.url(tomador))
        assert resp.data["data"]["seguradoras"] == [
            {"id": seguradora.id, "nome": "Alfa Seguros", "total": "0.00"}
        ]

    def test_seguradora_inativa_fica_de_fora(self, auth_client, tomador, seguradora):
        Seguradora.objects.create(
            nome="Beta Seguros", premio_minimo="500.00", ativo=False
        )

        resp = auth_client.get(self.url(tomador))
        nomes = [s["nome"] for s in resp.data["data"]["seguradoras"]]
        assert nomes == ["Alfa Seguros"]

    def test_flex_e_nulo_enquanto_nao_ha_regra(self, auth_client, tomador):
        resp = auth_client.get(self.url(tomador))
        assert resp.data["data"]["flex"] is None


# ─── Atividades do tomador ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestTomadorAtividadeList:
    def url(self, tomador):
        return reverse("tomador-atividades-list", args=[tomador.pk])

    def test_exige_autenticacao(self, client, tomador):
        resp = client.get(self.url(tomador))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_tomador_inexistente_retorna_404(self, auth_client):
        resp = auth_client.get(reverse("tomador-atividades-list", args=[9999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_registra_criacao_do_cadastro(self, auth_client, tomador):
        resp = auth_client.get(self.url(tomador))
        situacoes = [a["situacao"] for a in resp.data["data"]["results"]]
        assert "Criação do Cadastro" in situacoes

    def test_nao_vaza_atividade_de_tomador_homonimo(self, auth_client, tomador):
        """Regressão: o filtro por nome fazia cadastros homônimos compartilharem
        histórico. O vínculo agora é por `object_id`."""
        homonimo = Tomador.objects.create(cnpj="99.888.777/0001-66", nome=tomador.nome)
        Atividade.objects.create(
            entidade="Tomador",
            object_id=homonimo.pk,
            acao="ATUALIZAÇÃO",
            item=homonimo.nome,
            detalhes="mudou o do vizinho",
        )

        resp = auth_client.get(self.url(tomador))
        detalhes = [a["detalhes"] for a in resp.data["data"]["results"]]
        assert "mudou o do vizinho" not in detalhes

    def test_inclui_atividade_do_vinculo_com_seguradora(
        self, auth_client, tomador, seguradora
    ):
        TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=seguradora, taxa="1.50"
        )

        resp = auth_client.get(self.url(tomador))
        situacoes = [a["situacao"] for a in resp.data["data"]["results"]]
        assert "Atualização de Taxas - Alfa Seguros" in situacoes

    def test_pagina_invalida_nao_quebra(self, auth_client, tomador):
        """`?page=abc` estourava ValueError e devolvia 500."""
        resp = auth_client.get(self.url(tomador), {"page": "abc"})
        assert resp.status_code == status.HTTP_200_OK

    def test_pagina_zero_cai_para_primeira(self, auth_client, tomador):
        """`?page=0` gerava offset negativo e devolvia o fim da lista."""
        primeira = auth_client.get(self.url(tomador)).data["data"]["results"]
        zero = auth_client.get(self.url(tomador), {"page": 0}).data["data"]["results"]
        assert zero == primeira

    def test_pagina_com_dez_por_vez(self, auth_client, tomador):
        for i in range(15):
            Atividade.objects.create(
                entidade="Tomador",
                object_id=tomador.pk,
                acao="ATUALIZAÇÃO",
                item=tomador.nome,
                detalhes=f"alteração {i}",
            )

        primeira = auth_client.get(self.url(tomador)).data["data"]
        # 15 criadas aqui + a que o signal gravou ao criar o tomador
        assert primeira["count"] == 16
        assert len(primeira["results"]) == 10
        assert primeira["next"] == "?page=2"
        assert primeira["previous"] is None

        segunda = auth_client.get(self.url(tomador), {"page": 2}).data["data"]
        assert len(segunda["results"]) == 6
        assert segunda["next"] is None
        assert segunda["previous"] == "?page=1"
