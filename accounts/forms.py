from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Usuario


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(
            attrs={"autofocus": True, "placeholder": "seu@email.com", "class": "input"}
        ),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": "input"}),
    )
    lembrar = forms.BooleanField(required=False, label="Lembrar por 30 dias")


class UsuarioCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": "input"}),
        help_text="Mínimo 8 caracteres.",
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"class": "input"}),
    )

    class Meta:
        model = Usuario
        fields = ["email", "nome_completo", "cargo", "is_staff"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "input"}),
            "nome_completo": forms.TextInput(attrs={"class": "input"}),
            "cargo": forms.TextInput(attrs={"class": "input"}),
        }

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
        fields = ["email", "nome_completo", "cargo", "is_staff", "is_active"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "input"}),
            "nome_completo": forms.TextInput(attrs={"class": "input"}),
            "cargo": forms.TextInput(attrs={"class": "input"}),
        }


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["nome_completo", "cargo"]
        widgets = {
            "nome_completo": forms.TextInput(attrs={"class": "input"}),
            "cargo": forms.TextInput(attrs={"class": "input"}),
        }
