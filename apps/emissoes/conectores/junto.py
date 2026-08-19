"""Conector da Junto Seguros — API v2.

Toda a tradução entre o nosso vocabulário e o da Junto mora aqui. Quem está de
fora vê `DadosCotacao` entrando e `RespostaCotacao` saindo; `insuredAmount`,
`durationDays` e `totalPremiumValue` não vazam para o resto do sistema.

Doc: https://ms-gateway.juntoseguros.com/guarantee/documentation/v2
"""

import json
import logging
import threading
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from .base import (
    DadosCotacao,
    DadosSegurado,
    ErroSeguradora,
    ErroValidacaoSeguradora,
    OpcaoParcelamento,
    Parcela,
    Pendencia,
    RespostaCotacao,
    RespostaMinuta,
    SeguradoJunto,
    SeguradoraIndisponivel,
)

logger = logging.getLogger(__name__)

BASE_URLS = {
    "sandbox": "https://ms-gateway-box.juntoseguros.com",
    "producao": "https://ms-gateway.juntoseguros.com",
}

# 30s, não os 15s da spec: medido contra o sandbox, `POST /traditional` leva
# ~6s no caminho feliz, e 15s deixa margem estreita para o dia ruim deles.
# É ação disparada pelo usuário com spinner na tela, não job de background.
TIMEOUT_PADRAO = 30.0

# A minuta é outra ordem de grandeza: medida em 81s contra o sandbox em
# 2026-08-19, com o mesmo documento que dias antes respondera em menos de 60s.
# Com os 30s do padrão a chamada estourava e o usuário via "a seguradora não
# respondeu" para uma minuta que a Junto estava gerando normalmente.
TIMEOUT_MINUTA = 150.0

# Renova o token um pouco antes de expirar: uma chamada que sai com token no
# limite chega do outro lado já vencida.
MARGEM_TOKEN_SEGUNDOS = 60

MSG_INDISPONIVEL = "A seguradora não respondeu. Tente novamente."

# Cache de token por (seguradora, ambiente) — um id de sandbox não vale em
# produção, então o ambiente faz parte da chave.
_TOKEN_CACHE: dict[tuple[Any, str], tuple[str, float]] = {}
_TOKEN_LOCK = threading.Lock()


def limpar_cache_token() -> None:
    """Zera o cache. Existe para os testes não vazarem token entre si."""
    with _TOKEN_LOCK:
        _TOKEN_CACHE.clear()


def so_digitos(valor: str) -> str:
    return "".join(c for c in (valor or "") if c.isdigit())


def _iso_datetime(valor: date) -> str:
    """A Junto declara os campos de data como `date-time`."""
    return f"{valor.isoformat()}T00:00:00"


def _parse_data(valor: Any) -> date | None:
    if not valor:
        return None
    texto = str(valor).strip()
    if texto.endswith("Z"):
        texto = texto[:-1]
    try:
        return datetime.fromisoformat(texto).date()
    except ValueError:
        try:
            return datetime.strptime(texto[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _dec(valor: Any, *, default: Decimal | None = Decimal("0")) -> Decimal | None:
    """Converte para Decimal sem passar por float.

    O corpo já é desserializado com `parse_float=Decimal`; o `str()` aqui cobre
    int e valores que cheguem como texto. `Decimal(0.1)` valeria
    0.1000000000000000055511151231257827 e contaminaria prêmio e comissão.
    """
    if valor is None or valor == "":
        return default
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return default


class ConectorJunto:
    integracao = "junto"

    def __init__(self, seguradora, *, timeout: float = TIMEOUT_PADRAO, transport=None):
        self.seguradora = seguradora
        self.ambiente = seguradora.api_ambiente or "sandbox"
        if self.ambiente not in BASE_URLS:
            raise ErroSeguradora(
                f"Ambiente '{self.ambiente}' não é válido para a Junto Seguros."
            )
        self.base_url = BASE_URLS[self.ambiente]
        self.timeout = timeout
        self._transport = transport

    # ─── HTTP ────────────────────────────────────────────────────────────────

    def _cliente(self, timeout: float | None = None) -> httpx.Client:
        return httpx.Client(timeout=timeout or self.timeout, transport=self._transport)

    @staticmethod
    def _corpo_decimal(resp: httpx.Response) -> Any:
        try:
            return json.loads(resp.text, parse_float=Decimal)
        except ValueError:
            return {}

    @staticmethod
    def _corpo_bruto(resp: httpx.Response) -> Any:
        """Mesma resposta, com float, para gravar em JSONField de auditoria."""
        try:
            return json.loads(resp.text)
        except ValueError:
            return {"_texto": (resp.text or "")[:2000]}

    @classmethod
    def _mensagem_erro(cls, resp: httpx.Response) -> str:
        """A Junto devolve 400 como lista de `{message, errorCode}`."""
        corpo = cls._corpo_decimal(resp)
        if isinstance(corpo, list):
            mensagens = [
                str(item["message"])
                for item in corpo
                if isinstance(item, dict) and item.get("message")
            ]
            if mensagens:
                return " ".join(mensagens)
        if isinstance(corpo, dict):
            for chave in ("message", "detail", "title", "error"):
                if corpo.get(chave):
                    return str(corpo[chave])
        return ((resp.text or "").strip().strip('"') or "Requisição recusada.")[:500]

    # ─── Autenticação ────────────────────────────────────────────────────────

    def _chave_cache(self) -> tuple[Any, str]:
        return (self.seguradora.pk, self.ambiente)

    def _invalidar_token(self) -> None:
        with _TOKEN_LOCK:
            _TOKEN_CACHE.pop(self._chave_cache(), None)

    def _token(self, *, renovar: bool = False) -> str:
        agora = time.monotonic()
        if not renovar:
            with _TOKEN_LOCK:
                em_cache = _TOKEN_CACHE.get(self._chave_cache())
            if em_cache and em_cache[1] > agora:
                return em_cache[0]

        client_id = (self.seguradora.api_client_id or "").strip()
        client_secret = (self.seguradora.api_client_secret or "").strip()
        if not client_id or not client_secret:
            raise ErroValidacaoSeguradora("Credenciais da seguradora não configuradas.")

        url = f"{self.base_url}/guarantee/api/v2/authentication"
        try:
            with self._cliente() as cliente:
                resp = cliente.post(
                    url, json={"clientId": client_id, "clientSecret": client_secret}
                )
        except httpx.HTTPError as exc:
            # Sem `exc` na mensagem: a URL de auth carrega o corpo com o segredo
            # em alguns formatos de erro do httpx.
            logger.warning(
                "Junto: falha de rede na autenticação (%s)", type(exc).__name__
            )
            raise SeguradoraIndisponivel(MSG_INDISPONIVEL) from exc

        if resp.status_code >= 500:
            raise SeguradoraIndisponivel(MSG_INDISPONIVEL)
        if resp.status_code != 200:
            raise ErroValidacaoSeguradora(
                f"A seguradora recusou as credenciais: {self._mensagem_erro(resp)}"
            )

        corpo = self._corpo_decimal(resp)
        token = (corpo or {}).get("accessToken") or ""
        if not token:
            raise SeguradoraIndisponivel("A seguradora respondeu sem token de acesso.")

        # `expiresIn` vem da resposta, nunca de constante nossa: o sandbox
        # devolve 1800, não os 3600 que a documentação sugere.
        expira_em = int(corpo.get("expiresIn") or 0)
        validade = agora + max(expira_em - MARGEM_TOKEN_SEGUNDOS, 0)
        with _TOKEN_LOCK:
            _TOKEN_CACHE[self._chave_cache()] = (token, validade)
        return token

    def _chamar(
        self,
        metodo: str,
        caminho: str,
        *,
        payload: dict | None = None,
        timeout: float | None = None,
    ):
        """Chamada de negócio. Um 401 renova o token e repete uma única vez.

        `timeout` permite que uma etapa lenta (a minuta) espere mais sem
        afrouxar o limite das rápidas.
        """
        url = f"{self.base_url}{caminho}"
        resp = None
        for tentativa in (1, 2):
            token = self._token(renovar=tentativa == 2)
            try:
                with self._cliente(timeout) as cliente:
                    resp = cliente.request(
                        metodo,
                        url,
                        json=payload,
                        headers={"Authorization": f"Bearer {token}"},
                    )
            except httpx.HTTPError as exc:
                logger.warning(
                    "Junto: falha de rede em %s %s (%s)",
                    metodo,
                    caminho,
                    type(exc).__name__,
                )
                raise SeguradoraIndisponivel(MSG_INDISPONIVEL) from exc

            if resp.status_code == 401 and tentativa == 1:
                self._invalidar_token()
                continue
            break

        if resp.status_code == 401:
            raise SeguradoraIndisponivel("Não foi possível autenticar na seguradora.")
        if resp.status_code >= 500:
            raise SeguradoraIndisponivel(MSG_INDISPONIVEL)
        if resp.status_code >= 400:
            raise ErroValidacaoSeguradora(self._mensagem_erro(resp))
        return resp

    # ─── Cotação ─────────────────────────────────────────────────────────────

    def _payload_cotacao(self, dados: DadosCotacao) -> dict:
        codigo = (dados.modalidade_codigo or "").strip()
        if not codigo.isdigit():
            raise ErroValidacaoSeguradora(
                f"O código da modalidade na Junto precisa ser numérico (recebido: '{codigo}')."
            )

        cnpj = so_digitos(dados.tomador_cnpj)
        if not cnpj:
            raise ErroValidacaoSeguradora("O tomador precisa de CNPJ para cotar.")

        payload: dict[str, Any] = {
            "modalityId": int(codigo),
            "policyholderFederalId": cnpj,
            # float na saída é seguro: são 2 casas decimais e o repr do Python
            # devolve a menor string que faz round-trip. A disciplina de Decimal
            # vale na entrada, onde a precisão se perde.
            "insuredAmount": float(dados.importancia_segurada),
            "durationStart": _iso_datetime(dados.data_inicio),
            "durationDays": int(dados.prazo_dias),
            "additionGuarantee": {
                "isAdditionalLabor": dados.cobertura_adicional_trabalhista,
                "isAggravateCoverage50": dados.agravamento_50,
            },
            "isAdditionalFinesAndPenalties": dados.multas_e_penalidades,
            "isInProgress": dados.em_andamento,
            "isFidelizeProspection": dados.prospeccao_fidelize,
        }
        if dados.vencimento_primeira_parcela:
            payload["dueDateFirstInstallment"] = _iso_datetime(
                dados.vencimento_primeira_parcela
            )
        return payload

    def _parse_opcoes(self, corpo: dict) -> list[OpcaoParcelamento]:
        opcoes = []
        for bruta in corpo.get("installmentOptions") or []:
            parcelas = [
                Parcela(
                    numero=int(p.get("number") or 0),
                    vencimento=_parse_data(p.get("dueDate")),
                    valor=_dec(p.get("value")),
                    iof=_dec(p.get("iof")),
                    custo_apolice=_dec(p.get("policyCost")),
                    adicional_fracionamento=_dec(p.get("additionalOfFractionation")),
                )
                for p in (bruta.get("installments") or [])
            ]
            opcoes.append(
                OpcaoParcelamento(
                    numero_parcelas=int(bruta.get("numberOfInstallments") or 0),
                    vencimento_primeira_parcela=_parse_data(
                        bruta.get("dueDateFirstInstallment")
                    ),
                    premio_total=_dec(bruta.get("totalPremium")),
                    parcelas=parcelas,
                )
            )
        return opcoes

    def _parse_cotacao(
        self, resp: httpx.Response, payload: dict, *, external_id: str = ""
    ) -> RespostaCotacao:
        corpo = self._corpo_decimal(resp)
        if not isinstance(corpo, dict):
            raise SeguradoraIndisponivel(
                "A seguradora respondeu num formato inesperado."
            )

        # O PUT de atualização devolve 200 sem corpo em alguns casos; nesse
        # cenário o id que já tínhamos continua valendo.
        identificador = str(corpo.get("id") or external_id or "")
        if not identificador:
            raise SeguradoraIndisponivel(
                "A seguradora respondeu sem o identificador da cotação."
            )

        pricing = corpo.get("pricing") or {}
        return RespostaCotacao(
            external_id=identificador,
            premio_liquido=_dec(corpo.get("netPremiumValue")),
            premio_total=_dec(corpo.get("totalPremiumValue")),
            taxa=_dec(pricing.get("standardRate"), default=None),
            comissao_percentual=_dec(pricing.get("comissionRate"), default=None),
            comissao_valor=_dec(pricing.get("comissionValue"), default=None),
            numero_parcelas=(
                int(corpo["selectedNumberOfInstallments"])
                if corpo.get("selectedNumberOfInstallments")
                else None
            ),
            numero_max_parcelas=(
                int(corpo["numberOfMaxInstallments"])
                if corpo.get("numberOfMaxInstallments")
                else None
            ),
            opcoes_parcelamento=self._parse_opcoes(corpo),
            url_cotacao=str(corpo.get("urlQuote") or ""),
            request_bruto=payload,
            resposta_bruta=self._corpo_bruto(resp),
        )

    def cotar(self, *, dados: DadosCotacao) -> RespostaCotacao:
        payload = self._payload_cotacao(dados)
        resp = self._chamar("POST", "/guarantee/api/v2/traditional", payload=payload)
        return self._parse_cotacao(resp, payload)

    def atualizar_cotacao(
        self, *, external_id: str, dados: DadosCotacao
    ) -> RespostaCotacao:
        """Recotação. Um POST repetido criaria cotação órfã na Junto, contando
        contra o limite do tomador."""
        payload = self._payload_cotacao(dados)
        resp = self._chamar(
            "PUT", f"/guarantee/api/v2/traditional/{external_id}", payload=payload
        )
        return self._parse_cotacao(resp, payload, external_id=external_id)

    # ─── Segurado ────────────────────────────────────────────────────────────

    def _segurado_da_resposta(self, corpo: Any) -> SeguradoJunto | None:
        itens = corpo.get("data") if isinstance(corpo, dict) else corpo
        if not itens:
            return None
        primeiro = itens[0]
        if not primeiro.get("id"):
            return None
        enderecos = primeiro.get("address") or []
        return SeguradoJunto(
            insured_id=int(primeiro["id"]),
            # Com vários endereços a Junto aceita qualquer um dos ids; o
            # primeiro é o que a tela dela mostra por padrão.
            address_id=int(enderecos[0]["addressId"]) if enderecos else None,
        )

    def buscar_segurado(self, *, federal_id: str) -> SeguradoJunto | None:
        """Procura o segurado pelo CNPJ. `None` quando não existe lá.

        A busca sem nenhum parâmetro devolve 400 na Junto, então o CNPJ é
        obrigatório — quem chama já garante isso.
        """
        cnpj = so_digitos(federal_id)
        resp = self._chamar("GET", f"/guarantee/api/v2/insured?federalId={cnpj}")
        return self._segurado_da_resposta(self._corpo_bruto(resp))

    def cadastrar_segurado(self, *, dados: DadosSegurado) -> SeguradoJunto:
        """Cria o segurado na Junto. Só é chamado quando a busca não achou."""
        payload: dict[str, Any] = {
            "federalId": so_digitos(dados.federal_id),
            "name": dados.nome,
            "insuredType": dados.tipo,
            "address": {
                "street": dados.logradouro,
                "city": dados.cidade,
                "state": dados.uf,
                "zipCode": so_digitos(dados.cep),
                "addressComplement": dados.complemento,
            },
        }
        if dados.email:
            payload["email"] = dados.email
        if dados.telefone:
            payload["phone"] = dados.telefone

        resp = self._chamar("POST", "/guarantee/api/v2/insured", payload=payload)
        criado = self._segurado_da_resposta([self._corpo_bruto(resp)])
        if criado is None:
            raise SeguradoraIndisponivel(
                "A seguradora não devolveu o identificador do segurado criado."
            )
        return criado

    # ─── Minuta ──────────────────────────────────────────────────────────────

    def listar_pendencias(self, *, document_number: str) -> list[Pendencia]:
        """Pendências que travam a liberação do PDF pela seguradora."""
        resp = self._chamar(
            "GET", f"/guarantee/api/v2/policies/{document_number}/hangs"
        )
        corpo = self._corpo_bruto(resp)
        itens = corpo if isinstance(corpo, list) else (corpo.get("data") or [])
        pendencias = []
        for item in itens:
            dep = item.get("department") or {}
            pendencias.append(
                Pendencia(
                    codigo=int(item.get("code") or 0),
                    # A Junto manda espaço sobrando no fim das descrições.
                    descricao=str(item.get("description") or "").strip(),
                    departamento=str(dep.get("name") or "").strip(),
                    email=str(dep.get("email") or "").strip(),
                )
            )
        return pendencias

    def gerar_minuta(
        self,
        *,
        external_id: str,
        edital: str,
        segurado: SeguradoJunto,
        forcar_url: bool = False,
    ) -> RespostaMinuta:
        """Passo 2: gera a minuta da apólice.

        O bloco `insured` não é opcional na prática: sem ele a Junto devolve
        500 (`NullReferenceException`), verificado contra o sandbox. E o
        `draftUrl` vem vazio quando há pendência — só `isForceDraftUrl` destrava
        o PDF, o que é decisão do usuário, não nossa.
        """
        payload: dict[str, Any] = {
            "publicNoticeOrContract": edital,
            "insured": {"insuredId": segurado.insured_id},
        }
        if segurado.address_id is not None:
            payload["insured"]["insuredAddressId"] = segurado.address_id
        if forcar_url:
            payload["isForceDraftUrl"] = True

        resp = self._chamar(
            "PUT",
            f"/guarantee/api/v2/traditional/{external_id}/draft",
            payload=payload,
            timeout=TIMEOUT_MINUTA,
        )
        corpo = self._corpo_bruto(resp)
        if not isinstance(corpo, dict):
            raise SeguradoraIndisponivel(
                "A seguradora respondeu a minuta num formato inesperado."
            )

        document_number = str(corpo.get("documentNumber") or "")
        tem_pendencias = bool(corpo.get("hasHangs"))
        # Só consulta pendências quando há: uma chamada a menos no caminho feliz.
        pendencias = (
            self.listar_pendencias(document_number=document_number)
            if tem_pendencias and document_number
            else []
        )
        return RespostaMinuta(
            document_number=document_number,
            url_minuta=str(corpo.get("draftUrl") or ""),
            tem_pendencias=tem_pendencias,
            pendencias=pendencias,
            request_bruto=payload,
            resposta_bruta=corpo,
        )
