"""Forms do app demandas. Tailwind via core.forms.aplicar_tailwind."""

from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory

from core.forms import aplicar_tailwind

from .models import (
    Anexo,
    Demanda,
    DemandaEntidade,
    DemandaPessoa,
    Encaminhamento,
    Interacao,
    Tema,
)


class DemandaForm(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = [
            "titulo",
            "descricao",
            "origem",
            "canal_entrada",
            "anonimo",
            "prioridade",
            "responsavel",
            "coordenacao_responsavel",
            "restrito",
            "prazo",
            "temas",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "prazo": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "temas": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Temas ativos + os já vinculados (preserva arquivados em edição).
        cond = Q(ativo=True)
        if self.instance and self.instance.pk:
            cond |= Q(pk__in=self.instance.temas.values_list("pk", flat=True))
        self.fields["temas"].queryset = Tema.objects.filter(cond).distinct()
        self.fields["responsavel"].required = False
        self.fields["responsavel"].empty_label = "— Não atribuído —"
        aplicar_tailwind(self)


class TemaForm(forms.ModelForm):
    class Meta:
        model = Tema
        fields = ["nome", "cor", "descricao"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "cor": forms.TextInput(attrs={"placeholder": "#XXXXXX", "maxlength": 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)


class DemandaPessoaForm(forms.ModelForm):
    class Meta:
        model = DemandaPessoa
        fields = ["pessoa", "papel", "observacao"]
        widgets = {
            "papel": forms.TextInput(attrs={"placeholder": "solicitante, afetada..."}),
            "observacao": forms.TextInput(attrs={"placeholder": "Opcional"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from pessoas.models import Pessoa

        self.fields["pessoa"].queryset = Pessoa.objects.ativas()
        aplicar_tailwind(self)


DemandaPessoaFormSet = inlineformset_factory(
    Demanda,
    DemandaPessoa,
    form=DemandaPessoaForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


class DemandaEntidadeForm(forms.ModelForm):
    class Meta:
        model = DemandaEntidade
        fields = ["entidade", "papel", "observacao"]
        widgets = {
            "papel": forms.TextInput(attrs={"placeholder": "representada, parceira..."}),
            "observacao": forms.TextInput(attrs={"placeholder": "Opcional"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from pessoas.models import Entidade

        self.fields["entidade"].queryset = Entidade.objects.filter(ativo=True)
        aplicar_tailwind(self)


DemandaEntidadeFormSet = inlineformset_factory(
    Demanda,
    DemandaEntidade,
    form=DemandaEntidadeForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


class InteracaoForm(forms.ModelForm):
    """Form base de interação. Schedule follow-up tratado em InteracaoComFollowupForm."""

    class Meta:
        model = Interacao
        fields = ["tipo", "conteudo", "status", "data_ocorrencia"]
        widgets = {
            "conteudo": forms.Textarea(attrs={"rows": 3}),
            "data_ocorrencia": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tipos manuais apenas. Devolutiva é exclusiva do fluxo de conclusão
        # (ADR 0043) — não aparece aqui pra evitar registro órfão sem mover status.
        manuais = [
            (k, v)
            for k, v in Interacao.TIPO_CHOICES
            if k
            not in (
                Interacao.TIPO_MUDANCA_STATUS,
                Interacao.TIPO_MUDANCA_RESPONSAVEL,
                Interacao.TIPO_MUDANCA_RESULTADO,
                Interacao.TIPO_ARQUIVAMENTO,
                Interacao.TIPO_REGISTRO_INICIAL,
                Interacao.TIPO_DEVOLUTIVA,
            )
        ]
        self.fields["tipo"].choices = manuais
        self.fields["status"].choices = [
            (Interacao.STATUS_REALIZADA, "Realizada"),
            (Interacao.STATUS_AGENDADA, "Agendada"),
        ]
        aplicar_tailwind(self)


class FollowupForm(forms.Form):
    """Campos extras quando o usuário marca 'criar follow-up' ao salvar uma
    interação realizada. Cria nova Interacao com status agendada e
    interacao_origem apontando para a interação que acabou de ser salva."""

    criar = forms.BooleanField(required=False, label="Criar follow-up")
    tipo = forms.ChoiceField(required=False, choices=Interacao.TIPO_CHOICES)
    data_ocorrencia = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )
    conteudo = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].choices = [
            (k, v)
            for k, v in Interacao.TIPO_CHOICES
            if k
            not in (
                Interacao.TIPO_MUDANCA_STATUS,
                Interacao.TIPO_MUDANCA_RESPONSAVEL,
                Interacao.TIPO_MUDANCA_RESULTADO,
                Interacao.TIPO_ARQUIVAMENTO,
                Interacao.TIPO_REGISTRO_INICIAL,
                Interacao.TIPO_DEVOLUTIVA,
            )
        ]
        aplicar_tailwind(self)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("criar"):
            faltando = [
                campo for campo in ("tipo", "data_ocorrencia", "conteudo") if not cleaned.get(campo)
            ]
            if faltando:
                raise forms.ValidationError(
                    f"Para criar follow-up, preencha: {', '.join(faltando)}."
                )
        return cleaned


class EncaminhamentoForm(forms.ModelForm):
    class Meta:
        model = Encaminhamento
        fields = [
            "destinatario_orgao",
            "destinatario_pessoa",
            "tipo_documento",
            "numero_documento",
            "data_envio",
            "prazo_resposta",
        ]
        widgets = {
            "data_envio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "prazo_resposta": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)


class EncaminhamentoRespostaForm(forms.ModelForm):
    """Form específico para registrar resposta de um encaminhamento."""

    class Meta:
        model = Encaminhamento
        fields = ["status", "data_resposta", "conteudo_resposta"]
        widgets = {
            "data_resposta": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "conteudo_resposta": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            (Encaminhamento.STATUS_RESPONDIDO_SAT, "Respondido (satisfatório)"),
            (Encaminhamento.STATUS_RESPONDIDO_INSAT, "Respondido (insatisfatório)"),
            (Encaminhamento.STATUS_SEM_RESPOSTA, "Sem resposta (encerrar manualmente)"),
        ]
        aplicar_tailwind(self)


class AnexoForm(forms.ModelForm):
    class Meta:
        model = Anexo
        fields = ["arquivo", "descricao"]
        widgets = {"descricao": forms.TextInput(attrs={"placeholder": "Opcional"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)

    def clean_arquivo(self):
        f = self.cleaned_data.get("arquivo")
        if not f:
            return f
        if f.size > Anexo.TAMANHO_MAXIMO_BYTES:
            raise forms.ValidationError(
                f"Arquivo excede o limite de {Anexo.TAMANHO_MAXIMO_BYTES // (1024*1024)} MB."
            )
        mime = getattr(f, "content_type", "") or ""
        if mime and mime not in Anexo.MIME_WHITELIST:
            raise forms.ValidationError(f"Tipo de arquivo não permitido: {mime}.")
        return f


class ConcluirDemandaForm(forms.Form):
    """Conclusão de demanda RESPONSIVA. A view cria Interacao(tipo=devolutiva)
    + atualiza resultado + status em transação atômica. Ver ADR 0043."""

    devolutiva_data = forms.DateField(
        label="Data da devolutiva",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    devolutiva_canal = forms.ChoiceField(label="Canal da devolutiva", choices=Demanda.CANAL_CHOICES)
    devolutiva_conteudo = forms.CharField(
        label="O que foi comunicado ao demandante",
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    resultado = forms.ChoiceField(label="Resultado material")
    resultado_observacao = forms.CharField(
        label="Observação do resultado",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resultado"].choices = [
            (k, v) for k, v in Demanda.RESULTADO_CHOICES if k != Demanda.RESULTADO_PENDENTE
        ]
        aplicar_tailwind(self)


class ConcluirAcaoForm(forms.ModelForm):
    """Conclusão de demanda PROATIVA. Sem devolutiva — só exige resultado classificado."""

    class Meta:
        model = Demanda
        fields = ["resultado", "resultado_observacao"]
        widgets = {"resultado_observacao": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resultado"].choices = [
            (k, v) for k, v in Demanda.RESULTADO_CHOICES if k != Demanda.RESULTADO_PENDENTE
        ]
        self.fields["resultado"].required = True
        aplicar_tailwind(self)


class ArquivarForm(forms.ModelForm):
    class Meta:
        model = Demanda
        fields = ["observacoes_arquivamento"]
        widgets = {"observacoes_arquivamento": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_tailwind(self)


class EstadoForm(forms.ModelForm):
    """Edição inline do painel administrativo da demanda (aside). ADR 0044.

    Cobre os 5 campos que mudam ao longo do dia: status, resultado,
    responsavel, coordenacao_responsavel e prazo. 'concluida' e 'arquivado'
    NÃO aparecem no select de status — esses estados são exclusivos do
    fluxo dedicado (CTA Concluir / botão Arquivar)."""

    class Meta:
        model = Demanda
        fields = ["status", "resultado", "responsavel", "coordenacao_responsavel", "prazo"]
        widgets = {"prazo": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        editaveis = [
            Demanda.STATUS_NOVO,
            Demanda.STATUS_EM_ANDAMENTO,
            Demanda.STATUS_AGUARDANDO_TERCEIROS,
            Demanda.STATUS_AGUARDANDO_PESSOA,
        ]
        self.fields["status"].choices = [
            (k, v) for k, v in Demanda.STATUS_CHOICES if k in editaveis
        ]
        # Se já saiu de 'pendente', não pode voltar (clean() proíbe).
        if (
            self.instance
            and self.instance.pk
            and self.instance.resultado != Demanda.RESULTADO_PENDENTE
        ):
            self.fields["resultado"].choices = [
                (k, v) for k, v in Demanda.RESULTADO_CHOICES if k != Demanda.RESULTADO_PENDENTE
            ]
        self.fields["responsavel"].required = False
        self.fields["responsavel"].empty_label = "— Não atribuído —"
        self.fields["prazo"].required = False
        aplicar_tailwind(self)
