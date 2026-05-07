"""Settings de desenvolvimento. DEBUG ativo, e-mail no console."""

from .base import *  # noqa: F401,F403

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
