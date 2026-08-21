"""Contrato que toda seguradora integrada implementa.

`services.py` conversa só com esta interface, nunca com a Junto diretamente. É
essa fronteira que faz a próxima seguradora ser um arquivo novo em vez de uma
reescrita — e é por isso que as dataclasses abaixo falam o *nosso* vocabulário
(`importancia_segurada`, `premio_total`), não o da seguradora da vez.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Protocol


class ErroSeguradora(Exception):
    """Falha ao conversar com a seguradora."""


class ErroValidacaoSeguradora(ErroSeguradora):
    """A seguradora recusou os dados enviados.

    A mensagem é acionável pelo usuário ("CNPJ não cadastrado", "limite
    insuficiente") e por isso é repassada tal como veio.
    """


class SeguradoraIndisponivel(ErroSeguradora):
    """Rede, timeout ou 5xx.

    Distinta de `ErroValidacaoSeguradora` porque o usuário não tem o que
    corrigir: o caminho é tentar de novo.
    """


class IntegracaoNaoSuportada(ErroSeguradora):
    """A seguradora não tem conector registrado para o valor de `integracao`."""


@dataclass(frozen=True)
class DadosCotacao:
    """O que precisamos mandar para a seguradora cotar."""

    modalidade_codigo: str
    tomador_cnpj: str
    importancia_segurada: Decimal
    data_inicio: date
    prazo_dias: int
    vencimento_primeira_parcela: date | None = None
    cobertura_adicional_trabalhista: bool = False
    agravamento_50: bool = False
    multas_e_penalidades: bool = False
    em_andamento: bool = False
    prospeccao_fidelize: bool = False


@dataclass(frozen=True)
class Parcela:
    numero: int
    vencimento: date | None
    valor: Decimal
    iof: Decimal
    custo_apolice: Decimal
    adicional_fracionamento: Decimal


@dataclass(frozen=True)
class OpcaoParcelamento:
    numero_parcelas: int
    vencimento_primeira_parcela: date | None
    premio_total: Decimal
    parcelas: list[Parcela]


@dataclass(frozen=True)
class RespostaCotacao:
    """O que a seguradora devolveu, já traduzido.

    `request_bruto` e `resposta_bruta` viajam junto para auditoria: ficam em
    `EmissaoSeguradora.ultimo_request` / `.ultima_resposta` e nunca são
    serializados para o cliente.
    """

    external_id: str
    premio_liquido: Decimal
    premio_total: Decimal
    taxa: Decimal | None
    comissao_percentual: Decimal | None
    comissao_valor: Decimal | None
    numero_parcelas: int | None
    numero_max_parcelas: int | None
    opcoes_parcelamento: list[OpcaoParcelamento]
    url_cotacao: str = ""
    request_bruto: dict[str, Any] = field(default_factory=dict)
    resposta_bruta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DadosSegurado:
    """O que a Junto exige para cadastrar um segurado (`POST /insured`)."""

    federal_id: str
    nome: str
    # 8 = empresa pública, 9 = empresa privada. Não há terceira opção na API.
    tipo: int
    logradouro: str
    cidade: str
    uf: str
    cep: str
    complemento: str = ""
    email: str = ""
    telefone: str = ""


@dataclass(frozen=True)
class SeguradoJunto:
    """Identificadores do segurado do lado da seguradora."""

    insured_id: int
    address_id: int | None


@dataclass(frozen=True)
class TomadorSeguradoraInfo:
    """Cadastro do tomador do lado da seguradora.

    `valido_ate` é a validade do cadastro: a Junto expira o cadastro do tomador e
    um cadastro vencido não serve para emitir, então vale o mesmo que não ter.
    """

    cnpj: str
    nome: str
    cidade: str
    uf: str
    valido_ate: date | None


@dataclass(frozen=True)
class TaxaTomador:
    """Taxa e limite de uma modalidade do tomador."""

    taxa: Decimal
    modalidade_id: int
    modalidade_descricao: str
    limite_disponivel: Decimal


@dataclass(frozen=True)
class Pendencia:
    codigo: int
    descricao: str
    departamento: str
    email: str


@dataclass(frozen=True)
class RespostaMinuta:
    document_number: str
    url_minuta: str
    tem_pendencias: bool
    pendencias: list[Pendencia]
    request_bruto: dict[str, Any] = field(default_factory=dict)
    resposta_bruta: dict[str, Any] = field(default_factory=dict)


class ConectorSeguradora(Protocol):
    """Métodos que o `services.py` sabe chamar.

    Os passos seguintes do wizard (minuta, anexos, emissão, consulta) entram
    aqui conforme forem implementados.
    """

    def cotar(self, *, dados: DadosCotacao) -> RespostaCotacao: ...

    def atualizar_cotacao(
        self, *, external_id: str, dados: DadosCotacao
    ) -> RespostaCotacao: ...

    def buscar_segurado(self, *, federal_id: str) -> SeguradoJunto | None: ...

    def consultar_tomador(self, *, cnpj: str) -> TomadorSeguradoraInfo | None: ...

    def cadastrar_tomador(self, *, cnpj: str) -> None: ...

    def consultar_taxa_tomador(self, *, cnpj: str) -> TaxaTomador | None: ...

    def cadastrar_segurado(self, *, dados: DadosSegurado) -> SeguradoJunto: ...

    def gerar_minuta(
        self,
        *,
        external_id: str,
        edital: str,
        segurado: SeguradoJunto,
        forcar_url: bool = False,
    ) -> RespostaMinuta: ...
