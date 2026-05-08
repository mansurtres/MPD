"""Settings de produção. Não usado na Fase 0; existe pronto."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Só confiar em X-Forwarded-Proto quando atrás de proxy estrito que sanitize
# essa header (nginx, Caddy, Cloudflare). Caso contrário, clientes podem
# mandar a header e bypassar SSL_REDIRECT/Cookie_Secure. Ref: ADR 0033.
if env("DJANGO_TRUST_PROXY_SSL_HEADER"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
