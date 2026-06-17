from .base import *
import os

DEBUG = False

# Em produção a SECRET_KEY DEVE vir do ambiente — sem fallback inseguro.
SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', '').split(',')
    if host.strip()
]

# Origens confiáveis para CSRF (ex.: https://cajuina.com.br).
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

# Em produção restringimos CORS às origens explícitas em vez de liberar tudo.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]

# Configurações de segurança para produção
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True

# O Nginx faz o TLS na frente; este header informa ao Django que a conexão é segura.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
