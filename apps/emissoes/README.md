# apps/emissoes

Emissão de apólice integrada com a seguradora. Hoje cobre o **passo 1** do
wizard: criar a cotação na seguradora e trazer prêmio, taxa, comissão e opções
de parcelamento reais.

Spec: `docs/superpowers/specs/2026-08-13-emissao-apolice-junto-design.md`

## Como está organizado

```
conectores/base.py      contrato + dataclasses do nosso vocabulário + exceções
conectores/junto.py     tradução para a API v2 da Junto — o único arquivo que
                        conhece `insuredAmount`, `durationDays` etc.
conectores/registry.py  Seguradora.integracao -> classe do conector
services.py             regras, validações, lock e persistência
api/v1/                 endpoints do wizard
```

`services.py` fala só com a interface. Seguradora nova é um arquivo em
`conectores/` mais uma linha no registry — não uma reescrita.

## Endpoints

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/api/v1/cotacoes/{id}/emissao/cotar/` | cria (ou recalcula) a cotação na seguradora |
| `GET` | `/api/v1/cotacoes/{id}/emissao/` | estado persistido do wizard, sem tocar na seguradora |

Erros: `400` para o que o usuário pode corrigir (inclusive mensagem repassada da
seguradora), `502` para rede/timeout/5xx, `404` para cotação inexistente.

## Configuração

Na `Seguradora` (admin do Django):

| Campo | Valor |
|---|---|
| `integracao` | `junto` |
| `api_ambiente` | `sandbox` ou `producao` |
| `api_client_id` | clientId emitido pela Junto |
| `api_client_secret` | clientSecret emitido pela Junto |

A credencial mora no banco, não no `.env`: cada seguradora tem a sua, com o
próprio ambiente, trocável sem redeploy. `api_client_secret` é `write_only` —
entra por `POST`/`PATCH` e nunca sai em `GET`.

> As credenciais da **v1** (`api_usuario`, `api_senha`, `api_ou_name`,
> `api_source_app`) não servem para a v2 e serão removidas em migration própria.

## Modalidades

`ModalidadeSeguradora.codigo_seguradora` guarda o id da modalidade no catálogo da
seguradora. Sem o cadastro, cotar levanta `ModalidadeNaoMapeada`.

Catálogo da Junto v2 (confira o que está liberado para o tomador em
`GET /policyholders/{cnpj}/modalities` — nem toda modalidade vale para todos):

| ID | Modalidade |
|---:|---|
| 72 | Executante Concessionário – Convencional 662 (Com Salvamento) |
| 73 | Adiantamento de Pagamento |
| 75 | Imobiliário |
| 77 | Executante Construtor – Término de Obras – Infraestrutura |
| 79 | Parcelamento Administrativo Fiscal |
| 80 | Executante Construtor – Término de Obras |
| 81 | Aduaneiro – Admissão Temporária |
| 83 | Administrativo de Créditos Tributários |
| 89 | Financeira |
| 90 | Financeira – Pagamento de Energia |
| 91 | Financeira CUST/CUSD |
| 95 | Manutenção Corretiva – Convencional 662 (Com Salvamento) |
| 96 | Executante Construtor – Convencional 662 (Com Salvamento) |
| 97 | Executante Prestador de Serviços – Convencional 662 (Com Salvamento) |
| 98 | Executante Fornecedor – Convencional 662 (Com Salvamento) |
| 99 | Licitante |
| 121 | Processo Administrativo |

## Testar pelo shell

```bash
python manage.py emissao_cotar <cotacao_id>
```

Roda o mesmo serviço do endpoint, sem servidor nem token JWT.

## Decisões que não são óbvias no código

- **Timeout de 30s.** Medido contra o sandbox: `POST /traditional` leva ~6s no
  caminho feliz. Os 15s da spec deixavam margem estreita e estouraram em teste.
- **`expiresIn` vem da resposta**, nunca de constante: o sandbox devolve 1800,
  não os 3600 que a documentação sugere.
- **Segunda chamada a `cotar` vira `PUT`.** Um `POST` repetido cria cotação órfã
  na Junto, contando contra o limite do tomador.
- **Lock na `Cotacao`, não na `EmissaoSeguradora`**: na primeira chamada a
  emissão ainda não existe.
- **Dinheiro em `opcoes_parcelamento` é string.** Convertido explicitamente em
  `_opcoes_para_json`; sem isso o POST devolvia número e o GET string, para o
  mesmo campo.
- **`ultimo_request` / `ultima_resposta` nunca são serializados** para o cliente.
