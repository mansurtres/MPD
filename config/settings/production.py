"""Settings de produção. Mapa das variáveis no Render: docs/deploy.md."""

import sys

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Anexos vivem no disco persistente do Render. Fora do ponto de montagem o
# filesystem é efêmero: todo arquivo enviado some no deploy seguinte. Ref: ADR 0061.
MEDIA_ROOT = env("MEDIA_ROOT", default="/var/data/media")

# Origens confiáveis para POST sob HTTPS atrás do proxy. Sem isso, formulários
# rejeitam com "CSRF verification failed" em produção.
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Só confiar em X-Forwarded-Proto quando atrás de proxy estrito que sanitize
# essa header (nginx, Caddy, Cloudflare, Render). Caso contrário, clientes podem
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

# django-axes atrás de proxy: sem isto todo acesso chega com o IP do proxy e a
# auditoria de tentativa de login fica cega — o lockout continua funcionando
# (o par inclui username), mas o endereço registrado é inútil. Ref: ADR 0061.
AXES_IPWARE_PROXY_COUNT = env.int("DJANGO_PROXY_COUNT", default=1)
AXES_IPWARE_META_PRECEDENCE_ORDER = ("HTTP_X_FORWARDED_FOR", "REMOTE_ADDR")

# O Render captura a saída padrão como log do serviço. Sem isto, erro em
# produção não aparece em lugar nenhum.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simples": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "simples",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        # Segunda linha de defesa do registro de exportações (ADR 0053).
        "mpd.exports": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
