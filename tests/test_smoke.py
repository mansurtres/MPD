"""Smoke tests da Fase 0. Validam apenas que a infra está montada."""

from django.conf import settings


def test_django_imports():
    """Confirma que settings carrega sem erros."""
    assert settings.NOME_DO_MANDATO
    assert settings.AUTH_USER_MODEL == "accounts.Usuario"


def test_apps_locais_registrados():
    """Confirma que os 4 apps locais estão em INSTALLED_APPS."""
    apps_esperados = {"core", "accounts", "pessoas", "demandas"}
    instalados = set(settings.INSTALLED_APPS)
    assert apps_esperados.issubset(instalados)
