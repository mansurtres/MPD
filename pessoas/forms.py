"""Forms para Pessoa, Entidade, Vínculo e Tag."""

from django import forms

from .models import Entidade, Pessoa, Tag, Vinculo


class PessoaForm(forms.ModelForm):
    class Meta:
        model = Pessoa
        fields = [
            "nome",
            "sobrenome",
            "nome_social",
            "cpf",
            "data_nascimento",
            "genero",
            "email",
            "telefone",
            "whatsapp",
            "instagram",
            "cep",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "tags",
            "nao_telefonar",
            "nao_enviar_email",
            "nao_enviar_sms",
            "nao_compartilhar_dados",
            "observacoes",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
            "tags": forms.CheckboxSelectMultiple,
        }


class EntidadeForm(forms.ModelForm):
    class Meta:
        model = Entidade
        fields = [
            "nome",
            "nome_fantasia",
            "tipo",
            "cnpj",
            "email",
            "telefone",
            "site",
            "cep",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "tags",
            "observacoes",
        ]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 3}),
            "tags": forms.CheckboxSelectMultiple,
        }


class VinculoForm(forms.ModelForm):
    class Meta:
        model = Vinculo
        fields = ["entidade", "papel", "data_inicio", "data_fim", "observacao"]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "observacao": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, pessoa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._pessoa = pessoa
        self.fields["entidade"].queryset = Entidade.objects.ativas()

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self._pessoa is not None:
            instance.pessoa = self._pessoa
        if commit:
            instance.save()
        return instance


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["nome", "categoria", "cor", "descricao", "ativo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "cor": forms.TextInput(attrs={"type": "color"}),
        }
