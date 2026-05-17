"""Testes do app core: views institucionais e helpers compartilhados."""

from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.forms import aplicar_tailwind

Usuario = get_user_model()


# --- Views ---


def test_healthz_responde_ok(client, db):
    # /healthz verifica o banco; precisa da fixture db para ter conexão.
    response = client.get(reverse("core:healthz"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_inicio_anonimo_renderiza_publico(client):
    response = client.get(reverse("core:inicio"))
    assert response.status_code == 200
    templates = [t.name for t in response.templates if t.name]
    assert "core/inicio.html" in templates


def test_inicio_autenticado_renderiza_dashboard(client, db):
    user = Usuario.objects.create_user(
        email="dashboard@test.com",
        password="senha12345",  # pragma: allowlist secret
    )
    client.force_login(user)
    response = client.get(reverse("core:inicio"))
    assert response.status_code == 200
    templates = [t.name for t in response.templates if t.name]
    assert "core/inicio_autenticado.html" in templates


# --- aplicar_tailwind ---


class _FormDeTeste(forms.Form):
    texto = forms.CharField()
    flag = forms.BooleanField(required=False)


def test_aplicar_tailwind_injeta_classes_em_input_e_checkbox():
    f = _FormDeTeste()
    aplicar_tailwind(f)
    assert "rounded-lg" in f.fields["texto"].widget.attrs["class"]
    assert "rounded border-slate-300" in f.fields["flag"].widget.attrs["class"]


def test_aplicar_tailwind_idempotente():
    f = _FormDeTeste()
    aplicar_tailwind(f)
    aplicar_tailwind(f)
    classes = f.fields["texto"].widget.attrs["class"]
    assert classes.count("rounded-lg") == 1
