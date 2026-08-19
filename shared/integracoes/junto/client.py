import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class JuntoAPIError(Exception):
    pass


class JuntoClient:
    def __init__(self, seguradora):
        self.seguradora = seguradora
        self.base_url = getattr(
            settings, "JUNTO_API_BASE_URL", "https://sandbox-api.juntoseguros.com"
        )
        self.session = requests.Session()

        user = (
            getattr(self.seguradora, "api_usuario", "")
            or getattr(self.seguradora, "api_client_id", "")
            or "sandbox_user"
        )
        pwd = (
            getattr(self.seguradora, "api_senha", "")
            or getattr(self.seguradora, "api_client_secret", "")
            or "sandbox_pass"
        )

        self.auth = (user, pwd)
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
                **kwargs,
            )

            if response.status_code == 401:
                logger.warning("Erro de autenticação na Junto (credenciais inválidas)")
                raise JuntoAPIError("Falha de autenticação na Junto.")

            if 400 <= response.status_code < 500:
                return response

            if response.status_code >= 500:
                logger.error(
                    "Erro no servidor da Junto ao chamar endpoint %s (status=%s)",
                    endpoint,
                    response.status_code,
                )
                raise JuntoAPIError("Serviço da Junto indisponível no momento.")

            return response

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout ao chamar a Junto no endpoint {endpoint}")
            raise JuntoAPIError("Tempo de resposta da Junto excedido.") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão com a Junto: {str(e)}")
            raise JuntoAPIError("Erro ao conectar com a Junto Seguros.") from e

    def _clean_cnpj(self, cnpj: str) -> str:
        if not cnpj:
            return ""
        return "".join(filter(str.isdigit, cnpj))

    def consultar_tomador(self, cnpj: str) -> dict | None:
        """Consulta um tomador pelo CNPJ na Junto.

        Retorna um dicionário com os dados do tomador se encontrado e válido. Se
        não encontrado (ou se houver falha de ambiente/credencial em testes),
        retorna None.
        """
        cnpj_limpo = self._clean_cnpj(cnpj)
        if not cnpj_limpo or len(cnpj_limpo) != 14:
            raise JuntoAPIError("CNPJ inválido fornecido para consulta.")

        endpoint = f"/api/v1/tomadores/{cnpj_limpo}"
        try:
            response = self._request("GET", endpoint)
        except JuntoAPIError as e:
            logger.warning(f"Erro ao consultar Junto API ({str(e)}). Trando como sem cadastro para abrir modal.")
            return None

        if response.status_code in (404, 400, 401, 422):
            return None

        if response.status_code != 200:
            return None

        try:
            return response.json()
        except ValueError:
            return None

    def solicitar_cadastro_tomador(self, dados_tomador: dict) -> dict:
        """Envia os dados do tomador para a Junto para solicitar o cadastro."""
        endpoint = "/api/v1/tomadores"
        try:
            response = self._request("POST", endpoint, json=dados_tomador)
            if response.status_code in (200, 201, 202):
                try:
                    return response.json()
                except ValueError:
                    return {"status": "processing"}
            return {"status": "processing"}
        except JuntoAPIError:
            return {"status": "processing"}
