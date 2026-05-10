from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Usuario

# Templates de accounts/ renderizam HTML manualmente (login.html, perfil.html,
# usuarios/form.html) — não usam {{ form.<campo> }}. Por isso os widgets aqui
# não precisam carregar classes Tailwind: o estilo vive nos templates.


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"autofocus": True, "placeholder": "seu@email.com"}),
    )
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)
    lembrar = forms.BooleanField(required=False, label="Lembrar por 30 dias")


class UsuarioCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
        help_text="Mínimo 8 caracteres.",
    )
    password2 = forms.CharField(label="Confirmar senha", widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ["email", "nome_completo", "cargo", "coordenacao", "is_staff"]

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("As senhas não coincidem.")
        if p1:
            validate_password(p1)
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UsuarioUpdateForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["email", "nome_completo", "cargo", "coordenacao", "is_staff", "is_active"]

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._editor = editor

    def clean_is_staff(self):
        """Mitigação tática (ADR 0040): bloqueia auto-rebaixamento/auto-promoção
        de `is_staff`. Proteção contra perda de acesso por engano. Solução
        arquitetural completa em DT-011."""
        novo = self.cleaned_data.get("is_staff", False)
        if (
            self._editor is not None
            and self.instance.pk == self._editor.pk
            and novo != self.instance.is_staff
        ):
            raise ValidationError("Você não pode alterar a sua própria permissão de administrador.")
        return novo


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["nome_completo", "cargo"]
