"""Forms para Pessoa, Entidade, Vínculo, Tag e canais de contato.

Canais (telefones, emails, redes sociais, sites) são plurais e compartilhados
entre Pessoa e Entidade (ADR 0057). Cada model de canal tem dois formsets
gerados via inlineformset_factory — um por dono — porque o factory exige
um `parent_model` fixo. Os dois formsets reaproveitam o mesmo Form base.
"""

from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory

from core.forms import aplicar_tailwind

from .models import EmailContato, Entidade, Pessoa, RedeSocial, Site, Tag, Telefone, Vinculo


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
        cond = Q(ativo=True)
        if self.instance and self.instance.pk:
            cond |= Q(pk__in=self.instance.tags.values_list("pk", flat=True))
        self.fields["tags"].queryset = Tag.objects.filter(cond).distinct()
        aplicar_tailwind(self)


# --- Forms base dos canais (compartilhados entre Pessoa e Entidade) ---


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


class EmailContatoForm(forms.ModelForm):
    class Meta:
        model = EmailContato
        fields = ["endereco", "rotulo"]
        widgets = {
            "endereco": forms.EmailInput(attrs={"placeholder": "exemplo@dominio.com"}),
            "rotulo": forms.TextInput(attrs={"placeholder": 'Opcional. Ex: "trabalho"'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)


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


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ["url", "rotulo"]
        widgets = {
            "url": forms.URLInput(attrs={"placeholder": "https://"}),
            "rotulo": forms.TextInput(attrs={"placeholder": 'Opcional. Ex: "institucional"'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)


# --- FormSets por dono ---
# Pessoa
TelefoneFormSet = inlineformset_factory(
    Pessoa,
    Telefone,
    form=TelefoneForm,
    fk_name="pessoa",
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
EmailContatoFormSet = inlineformset_factory(
    Pessoa,
    EmailContato,
    form=EmailContatoForm,
    fk_name="pessoa",
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
RedeSocialFormSet = inlineformset_factory(
    Pessoa,
    RedeSocial,
    form=RedeSocialForm,
    fk_name="pessoa",
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
SitePessoaFormSet = inlineformset_factory(
    Pessoa,
    Site,
    form=SiteForm,
    fk_name="pessoa",
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)

# Entidade
TelefoneEntidadeFormSet = inlineformset_factory(
    Entidade,
    Telefone,
    form=TelefoneForm,
    fk_name="entidade",
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
EmailEntidadeFormSet = inlineformset_factory(
    Entidade,
    EmailContato,
    form=EmailContatoForm,
    fk_name="entidade",
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
RedeSocialEntidadeFormSet = inlineformset_factory(
    Entidade,
    RedeSocial,
    form=RedeSocialForm,
    fk_name="entidade",
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
SiteEntidadeFormSet = inlineformset_factory(
    Entidade,
    Site,
    form=SiteForm,
    fk_name="entidade",
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
        cond = Q(ativo=True)
        if self.instance and self.instance.pk:
            cond |= Q(pk__in=self.instance.tags.values_list("pk", flat=True))
        self.fields["tags"].queryset = Tag.objects.filter(cond).distinct()
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
