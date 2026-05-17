"""Forms para Pessoa, Entidade, Vínculo, Tag, Telefone, Email e RedeSocial."""

from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory

from core.forms import aplicar_tailwind

from .models import EmailPessoa, Entidade, Pessoa, RedeSocial, Tag, Telefone, Vinculo


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
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
            "tags": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostra tags ativas + arquivadas que esta pessoa já tem (preserva
        # vínculos pré-arquivamento para não somem ao salvar).
        cond = Q(ativo=True)
        if self.instance and self.instance.pk:
            cond |= Q(pk__in=self.instance.tags.values_list("pk", flat=True))
        self.fields["tags"].queryset = Tag.objects.filter(cond).distinct()
        aplicar_tailwind(self)


class TelefoneForm(forms.ModelForm):
    class Meta:
        model = Telefone
        fields = ["numero", "tipo", "eh_whatsapp", "rotulo"]
        widgets = {
            "numero": forms.TextInput(attrs={"placeholder": "(XX) XXXXX-XXXX"}),
            "rotulo": forms.TextInput(attrs={"placeholder": "Opcional"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)


TelefoneFormSet = inlineformset_factory(
    Pessoa,
    Telefone,
    form=TelefoneForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


class EmailPessoaForm(forms.ModelForm):
    class Meta:
        model = EmailPessoa
        fields = ["endereco", "rotulo"]
        widgets = {
            "endereco": forms.EmailInput(attrs={"placeholder": "exemplo@dominio.com"}),
            "rotulo": forms.TextInput(attrs={"placeholder": 'Opcional. Ex: "trabalho"'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)


EmailPessoaFormSet = inlineformset_factory(
    Pessoa,
    EmailPessoa,
    form=EmailPessoaForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


class RedeSocialForm(forms.ModelForm):
    class Meta:
        model = RedeSocial
        fields = ["plataforma", "valor", "rotulo"]
        widgets = {
            "valor": forms.TextInput(attrs={"placeholder": "@usuario ou URL"}),
            "rotulo": forms.TextInput(
                attrs={"placeholder": 'Opcional (obrigatório se plataforma="Outro")'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)


RedeSocialFormSet = inlineformset_factory(
    Pessoa,
    RedeSocial,
    form=RedeSocialForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)


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
        self.fields["entidade"].widget.attrs["data-autocomplete"] = "entidade"
        aplicar_tailwind(self)

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
        fields = ["nome", "cor", "descricao"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "cor": forms.TextInput(attrs={"placeholder": "#XXXXXX", "maxlength": 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)
