import pytest
from django.contrib.auth import get_user_model
from django.db import DataError, IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.cotacoes.models import Cotacao
from apps.modalidades import selectors, services
from apps.modalidades.models import (
    Modalidade,
    ModalidadeNaoMapeada,
    ModalidadeSeguradora,
)
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador

User = get_user_model()

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="tester", password="senha123")


@pytest.fixture
def auth_client(client, user):
    resp = client.post(
        reverse("token_obtain_pair"),
        {"username": "tester", "password": "senha123"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def execucao(db):
    return Modalidade.objects.create(nome="Execução de Contrato")


@pytest.fixture
def licitacao(db):
    return Modalidade.objects.create(nome="Licitação")


@pytest.fixture
def porto(db):
    return Seguradora.objects.create(
        nome="Porto Seguro", premio_minimo="150.00", vencimento_dias=30
    )


@pytest.fixture
def junto(db):
    return Seguradora.objects.create(
        nome="Junto Seguros", premio_minimo="140.00", vencimento_dias=20
    )


@pytest.fixture
def tomador(db):
    return Tomador.objects.create(cnpj="12.345.678/0001-90", nome="Construtora Teste")


# ─── Autenticação ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAutenticacao:
    def test_listar_sem_token_retorna_401(self, client, execucao):
        resp = client.get(reverse("modalidade-seguradora-list", args=[execucao.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_matriz_sem_token_retorna_401(self, client, db):
        resp = client.get(reverse("modalidade-matriz"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_salvar_matriz_sem_token_retorna_401(self, client, db):
        resp = client.put(reverse("modalidade-matriz"), {"linhas": []}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Model ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestModel:
    def test_par_duplicado_viola_constraint(self, execucao, porto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=porto, codigo_seguradora="3"
        )
        with pytest.raises(IntegrityError):
            ModalidadeSeguradora.objects.create(
                modalidade=execucao, seguradora=porto, codigo_seguradora="9"
            )

    def test_mesma_modalidade_em_seguradoras_diferentes(self, execucao, porto, junto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=porto, codigo_seguradora="17"
        )
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=junto, codigo_seguradora="3"
        )
        assert execucao.seguradoras.count() == 2


# ─── Tradução: o fallback do legado não existe mais ───────────────────────────

@pytest.mark.django_db
class TestTraducao:
    def test_codigo_mapeado_e_retornado(self, execucao, junto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=junto, codigo_seguradora="3"
        )
        codigo = selectors.codigo_para_seguradora(
            modalidade=execucao, seguradora=junto
        )
        assert codigo == "3"

    def test_sem_mapeamento_levanta_erro(self, execucao, junto):
        """O legado devolvia o ID interno aqui; isso mandava a cotação para a
        modalidade errada sem ninguém perceber."""
        with pytest.raises(ModalidadeNaoMapeada):
            selectors.codigo_para_seguradora(modalidade=execucao, seguradora=junto)

    def test_mapeamento_inativo_levanta_erro(self, execucao, junto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=junto, codigo_seguradora="3", ativo=False
        )
        with pytest.raises(ModalidadeNaoMapeada):
            selectors.codigo_para_seguradora(modalidade=execucao, seguradora=junto)

    def test_caminho_inverso(self, execucao, junto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=junto, codigo_seguradora="3"
        )
        achada = selectors.modalidade_por_codigo(seguradora=junto, codigo="3")
        assert achada == execucao

    def test_caminho_inverso_sem_mapeamento_levanta_erro(self, junto):
        with pytest.raises(ModalidadeNaoMapeada):
            selectors.modalidade_por_codigo(seguradora=junto, codigo="999")

    def test_codigo_e_por_seguradora(self, execucao, porto, junto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=porto, codigo_seguradora="17"
        )
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=junto, codigo_seguradora="3"
        )
        assert selectors.codigo_para_seguradora(modalidade=execucao, seguradora=porto) == "17"
        assert selectors.codigo_para_seguradora(modalidade=execucao, seguradora=junto) == "3"


# ─── Upsert ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUpsert:
    def test_upsert_e_idempotente(self, execucao, porto):
        for _ in range(2):
            services.modalidade_seguradora_upsert(
                modalidade=execucao,
                seguradora=porto,
                data={"codigo_seguradora": "17"},
            )
        assert ModalidadeSeguradora.objects.filter(
            modalidade=execucao, seguradora=porto
        ).count() == 1

    def test_upsert_atualiza_codigo(self, execucao, porto):
        services.modalidade_seguradora_upsert(
            modalidade=execucao, seguradora=porto, data={"codigo_seguradora": "17"}
        )
        services.modalidade_seguradora_upsert(
            modalidade=execucao, seguradora=porto, data={"codigo_seguradora": "21"}
        )
        vinculo = ModalidadeSeguradora.objects.get(modalidade=execucao, seguradora=porto)
        assert vinculo.codigo_seguradora == "21"

    def test_codigo_em_branco_remove_mapeamento(self, execucao, porto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=porto, codigo_seguradora="17"
        )
        services.modalidade_seguradora_bulk_upsert(
            modalidade=execucao,
            itens=[{"seguradora": porto, "codigo_seguradora": ""}],
        )
        assert not ModalidadeSeguradora.objects.filter(
            modalidade=execucao, seguradora=porto
        ).exists()

    def test_bulk_nao_mexe_em_seguradora_fora_do_payload(self, execucao, porto, junto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=junto, codigo_seguradora="3"
        )
        services.modalidade_seguradora_bulk_upsert(
            modalidade=execucao,
            itens=[{"seguradora": porto, "codigo_seguradora": "17"}],
        )
        assert ModalidadeSeguradora.objects.get(
            modalidade=execucao, seguradora=junto
        ).codigo_seguradora == "3"


# ─── Endpoints do mapeamento ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestEndpointsMapeamento:
    def test_listar_mapeamentos(self, auth_client, execucao, porto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=porto, codigo_seguradora="17"
        )
        resp = auth_client.get(reverse("modalidade-seguradora-list", args=[execucao.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["codigo_seguradora"] == "17"
        assert resp.data["data"][0]["seguradora_nome"] == "Porto Seguro"

    def test_listar_modalidade_inexistente_retorna_404(self, auth_client, db):
        resp = auth_client.get(reverse("modalidade-seguradora-list", args=[9999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_put_salva_varias_seguradoras(self, auth_client, execucao, porto, junto):
        resp = auth_client.put(
            reverse("modalidade-seguradora-list", args=[execucao.pk]),
            {
                "itens": [
                    {"seguradora": porto.pk, "codigo_seguradora": "17"},
                    {"seguradora": junto.pk, "codigo_seguradora": "3"},
                ]
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert execucao.seguradoras.count() == 2

    def test_put_com_seguradora_repetida_retorna_400(self, auth_client, execucao, porto):
        resp = auth_client.put(
            reverse("modalidade-seguradora-list", args=[execucao.pk]),
            {
                "itens": [
                    {"seguradora": porto.pk, "codigo_seguradora": "17"},
                    {"seguradora": porto.pk, "codigo_seguradora": "21"},
                ]
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_detalhe_de_par_nao_mapeado_retorna_404(self, auth_client, execucao, porto):
        resp = auth_client.get(
            reverse("modalidade-seguradora-detail", args=[execucao.pk, porto.pk])
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_remove_mapeamento(self, auth_client, execucao, porto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=porto, codigo_seguradora="17"
        )
        resp = auth_client.delete(
            reverse("modalidade-seguradora-detail", args=[execucao.pk, porto.pk])
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not ModalidadeSeguradora.objects.filter(
            modalidade=execucao, seguradora=porto
        ).exists()


# ─── Matriz ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMatriz:
    def test_get_monta_grade_completa(self, auth_client, execucao, licitacao, porto, junto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=junto, codigo_seguradora="3"
        )
        resp = auth_client.get(reverse("modalidade-matriz"))
        assert resp.status_code == status.HTTP_200_OK

        dados = resp.data["data"]
        assert len(dados["seguradoras"]) == 2
        assert len(dados["modalidades"]) == 2

        linha = next(m for m in dados["modalidades"] if m["id"] == execucao.pk)
        assert linha["codigos"][str(junto.pk)] == "3"
        # Célula sem mapeamento vem vazia, não ausente: a tela precisa do input.
        assert linha["codigos"][str(porto.pk)] == ""

    def test_get_ignora_inativos(self, auth_client, execucao, porto, db):
        Modalidade.objects.create(nome="Descontinuada", ativo=False)
        Seguradora.objects.create(
            nome="Inativa", premio_minimo="100.00", ativo=False
        )
        resp = auth_client.get(reverse("modalidade-matriz"))
        dados = resp.data["data"]
        assert [m["nome"] for m in dados["modalidades"]] == ["Execução de Contrato"]
        assert [s["nome"] for s in dados["seguradoras"]] == ["Porto Seguro"]

    def test_put_salva_matriz_inteira(self, auth_client, execucao, licitacao, porto, junto):
        resp = auth_client.put(
            reverse("modalidade-matriz"),
            {
                "linhas": [
                    {
                        "modalidade": execucao.pk,
                        "itens": [
                            {"seguradora": porto.pk, "codigo_seguradora": "17"},
                            {"seguradora": junto.pk, "codigo_seguradora": "3"},
                        ],
                    },
                    {
                        "modalidade": licitacao.pk,
                        "itens": [
                            {"seguradora": porto.pk, "codigo_seguradora": "5"},
                            {"seguradora": junto.pk, "codigo_seguradora": ""},
                        ],
                    },
                ]
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert ModalidadeSeguradora.objects.count() == 3

        linha = next(
            m for m in resp.data["data"]["modalidades"] if m["id"] == licitacao.pk
        )
        assert linha["codigos"][str(porto.pk)] == "5"
        assert linha["codigos"][str(junto.pk)] == ""

    def test_put_com_modalidade_inexistente_nao_grava_nada(
        self, auth_client, execucao, licitacao, porto
    ):
        """Validação barra a matriz inteira antes de tocar no banco."""
        resp = auth_client.put(
            reverse("modalidade-matriz"),
            {
                "linhas": [
                    {
                        "modalidade": execucao.pk,
                        "itens": [{"seguradora": porto.pk, "codigo_seguradora": "17"}],
                    },
                    {
                        "modalidade": 9999,
                        "itens": [{"seguradora": porto.pk, "codigo_seguradora": "5"}],
                    },
                ]
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert ModalidadeSeguradora.objects.count() == 0

    def test_erro_de_gravacao_desfaz_a_matriz_inteira(self, execucao, licitacao, porto):
        """Rollback real: a falha acontece no banco, depois da validação.

        Um código acima de 50 caracteres só é recusado na hora do INSERT, então
        a primeira linha já está gravada quando a segunda estoura. Sem o
        @transaction.atomic, a matriz ficaria meio salva.
        """
        with pytest.raises(DataError):
            services.matriz_salvar(
                linhas=[
                    {
                        "modalidade": execucao,
                        "itens": [{"seguradora": porto, "codigo_seguradora": "17"}],
                    },
                    {
                        "modalidade": licitacao,
                        "itens": [{"seguradora": porto, "codigo_seguradora": "X" * 60}],
                    },
                ]
            )
        assert ModalidadeSeguradora.objects.count() == 0

    def test_put_com_modalidade_repetida_retorna_400(self, auth_client, execucao, porto):
        resp = auth_client.put(
            reverse("modalidade-matriz"),
            {
                "linhas": [
                    {
                        "modalidade": execucao.pk,
                        "itens": [{"seguradora": porto.pk, "codigo_seguradora": "17"}],
                    },
                    {
                        "modalidade": execucao.pk,
                        "itens": [{"seguradora": porto.pk, "codigo_seguradora": "21"}],
                    },
                ]
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Ajustes no CRUD existente ────────────────────────────────────────────────

@pytest.mark.django_db
class TestFiltroPorSeguradora:
    def test_lista_so_modalidades_da_seguradora(
        self, auth_client, execucao, licitacao, porto
    ):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=porto, codigo_seguradora="17"
        )
        resp = auth_client.get(
            reverse("modalidade-list-create"), {"seguradora": porto.pk}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert [m["nome"] for m in resp.data["data"]] == ["Execução de Contrato"]

    def test_mapeamento_inativo_fica_fora(self, auth_client, execucao, porto):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=porto, codigo_seguradora="17", ativo=False
        )
        resp = auth_client.get(
            reverse("modalidade-list-create"), {"seguradora": porto.pk}
        )
        assert resp.data["data"] == []

    def test_sem_filtro_lista_todas(self, auth_client, execucao, licitacao):
        resp = auth_client.get(reverse("modalidade-list-create"))
        assert len(resp.data["data"]) == 2


@pytest.mark.django_db
class TestExclusaoProtegida:
    def test_modalidade_com_cotacao_retorna_400(
        self, auth_client, execucao, tomador, user
    ):
        Cotacao.objects.create(tomador=tomador, modalidade=execucao, criado_por=user)
        resp = auth_client.delete(reverse("modalidade-detail", args=[execucao.pk]))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert Modalidade.objects.filter(pk=execucao.pk).exists()

    def test_modalidade_sem_cotacao_e_excluida(self, auth_client, execucao):
        resp = auth_client.delete(reverse("modalidade-detail", args=[execucao.pk]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Modalidade.objects.filter(pk=execucao.pk).exists()

    def test_excluir_modalidade_leva_mapeamentos_junto(
        self, auth_client, execucao, porto
    ):
        ModalidadeSeguradora.objects.create(
            modalidade=execucao, seguradora=porto, codigo_seguradora="17"
        )
        resp = auth_client.delete(reverse("modalidade-detail", args=[execucao.pk]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert ModalidadeSeguradora.objects.count() == 0
