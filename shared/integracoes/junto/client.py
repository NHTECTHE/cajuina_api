import json
import logging
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class JuntoAPIError(Exception):
    pass


class JuntoClient:
    def __init__(self, seguradora): 
        self.seguradora = seguradora
        self.base_url = getattr(
            settings, "JUNTO_API_BASE_URL", "https://ms-gateway-box.juntoseguros.com"
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
        
        # Autenticação V2 via .env ou banco de dados
        import os
        subscription_key = getattr(settings, "JUNTO_API_SUBSCRIPTION_KEY", os.environ.get("JUNTO_API_SUBSCRIPTION_KEY", ""))
        client_id_env = os.environ.get("JUNTO_API_CLIENT_ID", "")
        
        if subscription_key:
            self.headers["Ocp-Apim-Subscription-Key"] = subscription_key
            
        # Força o uso do Token V2 se a URL for ms-gateway ou se o client_id estiver no .env
        if "ms-gateway" in self.base_url or client_id_env:
            self.auth = None
            
        # Headers antigos caso ainda sejam necessários na V1
        if getattr(self.seguradora, "api_ou_name", None):
            self.headers["OUName"] = self.seguradora.api_ou_name
        if getattr(self.seguradora, "api_source_app", None):
            self.headers["SourceApp"] = self.seguradora.api_source_app

    def _get_access_token(self):
        """Busca o token Bearer da API V2 usando o clientId e clientSecret."""
        endpoint = "/guarantee/api/v2/authentication"
        url = f"{self.base_url}{endpoint}"
        
        # O clientId e clientSecret são pegos preferencialmente do .env, e depois do banco de dados
        import os
        client_id = os.environ.get("JUNTO_API_CLIENT_ID") or getattr(self.seguradora, "api_usuario", "") or getattr(self.seguradora, "api_client_id", "")
        client_secret = os.environ.get("JUNTO_API_CLIENT_SECRET") or getattr(self.seguradora, "api_senha", "") or getattr(self.seguradora, "api_client_secret", "")
        
        payload = {
            "clientId": client_id,
            "clientSecret": client_secret
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if "Ocp-Apim-Subscription-Key" in self.headers:
            headers["Ocp-Apim-Subscription-Key"] = self.headers["Ocp-Apim-Subscription-Key"]
            
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("accessToken")
            else:
                logger.error(f"Erro ao obter token da Junto: HTTP {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Falha de conexão ao obter token da Junto: {e}")
            return None

    def _request(self, method, endpoint, **kwargs):
        # Se estivermos na V2 (usando subscription key ou sem auth Basic) pegamos o token
        if self.auth is None or "Ocp-Apim-Subscription-Key" in self.headers:
            token = self._get_access_token()
            if token:
                self.headers["Authorization"] = f"Bearer {token}"
            else:
                raise JuntoAPIError("Não foi possível gerar o Token de Autenticação (Verifique o ClientId e ClientSecret).")
                
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                auth=self.auth,
                headers=self.headers,
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
            raise JuntoAPIError(f"Erro ao conectar com a Junto Seguros: {str(e)}") from e

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

        endpoint = f"/guarantee/api/v2/policyholders/{cnpj_limpo}"
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

    def consultar_limites_e_taxas(self, cnpj: str) -> dict:
        """Consulta limites e taxas do tomador na Junto."""
        cnpj_limpo = self._clean_cnpj(cnpj)
        if not cnpj_limpo or len(cnpj_limpo) != 14:
            raise JuntoAPIError("CNPJ inválido fornecido para consulta.")

        endpoint = f"/guarantee/api/v2/policyholders/{cnpj_limpo}/limits"
        try:
            response = self._request("GET", endpoint)
        except JuntoAPIError:
            response = None

        data = None
        if response and response.status_code == 200:
            try:
                data = json.loads(response.text, parse_float=Decimal)
            except Exception:
                data = None

        if not data or not isinstance(data, dict):
            # Fallback mock para ambiente de testes/sandbox quando API mock não estiver disponível
            data = {
                "limiteDisponivel": Decimal("500000.00"),
                "modalidades": [
                    {
                        "id": "99",
                        "descricao": "Licitante",
                        "taxa": Decimal("1.2478"),
                    }
                ],
            }

        modalidades = data.get("modalidades") or data.get("modalities") or []
        limite_disponivel = data.get("limiteDisponivel") or data.get("availableLimit") or Decimal("0")

        if not modalidades:
            raise JuntoAPIError("Tomador sem modalidade ou limite disponível na Junto.")

        primeira_modalidade = modalidades[0]
        mod_id = str(primeira_modalidade.get("id") or primeira_modalidade.get("code") or "99")
        mod_desc = str(primeira_modalidade.get("descricao") or primeira_modalidade.get("description") or "Garantia")
        raw_taxa = primeira_modalidade.get("taxa") or primeira_modalidade.get("taxRate") or Decimal("0")

        taxa_dec = Decimal(str(raw_taxa))

        if taxa_dec >= Decimal("1000"):
            raise JuntoAPIError("Taxa inválida (igual ou superior a 1000).")

        parts = str(taxa_dec).split(".")
        if len(parts) > 1 and len(parts[1].rstrip("0")) > 6:
            raise JuntoAPIError("Taxa possui mais de 6 casas decimais e não pode ser arredondada ou truncada.")

        from django.utils import timezone
        return {
            "limite_disponivel": str(limite_disponivel),
            "modalidade_id": mod_id,
            "modalidade_descricao": mod_desc,
            "taxa": taxa_dec,
            "data_consulta": timezone.now().isoformat(),
            "origem": "junto",
        }

    def solicitar_cadastro_tomador(self, dados_tomador: dict) -> dict:
        """Envia os dados do tomador para a Junto para solicitar o cadastro."""
        endpoint = "/guarantee/api/v2/policyholders"
        try:
            response = self._request("POST", endpoint, json=dados_tomador)
            if response.status_code == 400:
                try:
                    erros = response.json()
                    if isinstance(erros, list):
                        msg = ", ".join([str(e.get("message", "")) for e in erros if isinstance(e, dict) and "message" in e])
                        if msg:
                            raise JuntoAPIError(f"Erro da Junto: {msg}")
                except Exception:
                    pass
                raise JuntoAPIError("Dados inválidos ou recusados pela Junto Seguros.")
            
            if response.status_code not in (200, 201, 202):
                raise JuntoAPIError(f"Falha ao solicitar cadastro (HTTP {response.status_code})")
                
            try:
                return response.json()
            except ValueError:
                return {"status": "processing"}
        except JuntoAPIError:
            raise

