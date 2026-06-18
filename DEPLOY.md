# Deploy — Cajuína API

CI/CD via GitHub Actions. O CI roda lint + testes em cada push/PR; o deploy faz SSH na VPS
após o CI passar na `main`.

## 1. Setup inicial da VPS (uma vez)

Pré-requisitos: Docker + Docker Compose plugin instalados.

```bash
# Rede compartilhada entre api e web (criada uma única vez para os dois repos)
docker network create cajuina-net

# Clonar o repositório
git clone <url-do-repo-cajuina_api> /opt/cajuina_api
cd /opt/cajuina_api

# Criar o .env de produção a partir do exemplo e preencher os valores
cp .env.example .env
nano .env   # gere a SECRET_KEY, defina ALLOWED_HOSTS, senha do Postgres, etc.
```

> A rede `cajuina-net` é compartilhada com o repo `cajuina` (frontend). Crie-a apenas uma vez.

## 2. Secrets do GitHub (repo cajuina_api)

Em **Settings → Secrets and variables → Actions**:

| Secret | Valor |
|--------|-------|
| `VPS_HOST` | IP ou hostname da VPS |
| `VPS_USER` | usuário SSH (ex.: `deploy`) |
| `VPS_SSH_KEY` | chave **privada** SSH com acesso à VPS |
| `VPS_PROJECT_PATH` | caminho do repo na VPS (ex.: `/opt/cajuina_api`) |

A chave pública correspondente deve estar em `~/.ssh/authorized_keys` do `VPS_USER`.

## 3. Primeiro deploy

Faça push na `main` (ou rode o workflow **Deploy** manualmente em Actions). O deploy:

1. `git reset --hard origin/main` no diretório do projeto
2. `docker compose -f docker-compose.prod.yml up -d --build`
3. `migrate` + `collectstatic`

## 4. Nginx (exemplo)

Reverse proxy no host, com a API exposta apenas em `127.0.0.1:8000`:

```nginx
server {
    listen 80;
    server_name api.cajuina.com.br;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/cajuina_api/staticfiles/;
    }
}
```

Use Certbot (`certbot --nginx`) para o TLS. O `SECURE_PROXY_SSL_HEADER` em `production.py`
já reconhece o `X-Forwarded-Proto`.

## Comandos úteis

```bash
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml run --rm api python manage.py createsuperuser
```
