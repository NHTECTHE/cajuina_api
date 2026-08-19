import logging
import requests
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class JuntoAPIError(Exception):
    pass

class JuntoClient:
    def __init__(self, seguradora):
        self.seguradora = seguradora
        self.base_url = getattr(settings, "JUNTO_API_BASE_URL", "https://sandbox-api.juntoseguros.com")
        self.session = requests.Session()

        # Verify credentials exist
        if not getattr(self.seguradora, "api_usuario", None) or not getattr(self.seguradora, "api_senha", None):
            raise JuntoAPIError("Credenciais da Junto Seguros não configuradas na seguradora.")

        self.auth = (self.seguradora.api_usuario, self.seguradora.api_senha)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if getattr(self.seguradora, "api_ou_name", None):
            self.headers["OUName"] = self.seguradora.api_ou_name
        if getattr(self.seguradora, "api_source_app", None):
            self.headers["SourceApp"] = self.seguradora.api_source_app

    def _request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                auth=self.auth,
                headers=self.headers,
                timeout=10,
                **kwargs
            )

            if response.status_code == 401:
                logger.warning("Erro de autenticação na Junto (credenciais inválidas)")
                raise JuntoAPIError("Falha de autenticação na Junto.")

            # Cliente ou validação (4xx) — permitimos que chamadores façam a leitura
            # do corpo para apresentar mensagens mais amigáveis; não logamos
            # conteúdo sensível aqui (tokens/credentials).
            if 400 <= response.status_code < 500:
                return response

            if response.status_code >= 500:
                logger.error("Erro no servidor da Junto ao chamar endpoint %s (status=%s)", endpoint, response.status_code)
                raise JuntoAPIError("Serviço da Junto indisponível no momento.")

            return response

        except requests.exceptions.Timeout:
            logger.error(f"Timeout ao chamar a Junto no endpoint {endpoint}")
            raise JuntoAPIError("Tempo de resposta da Junto excedido.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão com a Junto: {str(e)}")
            raise JuntoAPIError("Erro ao conectar com a Junto Seguros.")

    def _clean_cnpj(self, cnpj: str) -> str:
        if not cnpj:
            return ""
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        return cnpj_limpo

    def consultar_tomador(self, cnpj: str) -> dict | None:
        """
        Consulta um tomador pelo CNPJ na Junto.
        Retorna um dicionário com os dados do tomador se encontrado e válido.
        Se não encontrado, retorna None.
        """
        cnpj_limpo = self._clean_cnpj(cnpj)
        if not cnpj_limpo or len(cnpj_limpo) != 14:
            raise JuntoAPIError("CNPJ inválido fornecido para consulta.")

        endpoint = f"/api/v1/tomadores/{cnpj_limpo}"
        response = self._request("GET", endpoint)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            # tenta extrair mensagem amigável do corpo json, sem logar dados
            try:
                body = response.json()
                msg = body.get("message") or body.get("detail") or str(body)
            except ValueError:
                msg = response.text
            raise JuntoAPIError(f"Erro ao consultar tomador: {msg}")

        try:
            return response.json()
        except ValueError:
            raise JuntoAPIError("Resposta inválida da Junto ao consultar tomador.")

    def solicitar_cadastro_tomador(self, dados_tomador: dict) -> dict:
        """
        Envia os dados do tomador para a Junto para solicitar o cadastro.
        """
        endpoint = "/api/v1/tomadores"
        response = self._request("POST", endpoint, json=dados_tomador)

        if response.status_code in (200, 201, 202):
            try:
                return response.json()
            except ValueError:
                # Resposta sem JSON: devolve um resumo
                return {"status": str(response.status_code)}

        # Erros 4xx — tenta extrair mensagens de validação
        try:
            body = response.json()
        except ValueError:
            body = {"error": response.text}

        raise JuntoAPIError(f"Erro de validação na Junto ao cadastrar: {body}")
