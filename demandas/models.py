"""Models do app demandas — coração operacional do MPD.

Demanda tem dois eixos independentes (status, resultado). A regra de
fechamento bifurca por origem (ADR 0043):
- Responsiva: status='concluida' exige Interacao(tipo=devolutiva) + resultado classificado.
- Proativa:   status='concluida' exige apenas resultado classificado.

Devolutiva ao demandante NÃO é mais campo da Demanda — é Interação de
tipo 'devolutiva' na timeline (ato de primeira classe).

Geração de número thread-safe via select_for_update no método de classe
Demanda.gerar_numero(). Mudanças de estado disparam signals que criam
Interacoes automáticas (pessoas/signals.py para o pattern).

Tema (model próprio) categoriza Demanda — diferente de pessoas.Tag que
caracteriza Pessoa/Entidade. Decisão registrada em ADR 0042 (supersede
parcialmente ADR 0039 para o domínio de demandas).
"""

import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from core.mixins import AuditavelMixin
from core.utils import gerar_slug_publico


def _q_demanda_visivel_para(user):
    """Predicado Q de visibilidade de demanda.

    Usado por DemandaQuerySet.visiveis_para e por Demanda.q_visivel_para
    (classmethod para uso em queries externas como PessoaDetailView).
    Retorna None se o usuário tem acesso irrestrito (CG+).
    """
    from core.permissoes import eh_cg_plus

    if eh_cg_plus(user):
        return None
    return models.Q(restrito=False) | models.Q(responsavel=user)


class DemandaQuerySet(models.QuerySet):
    def visiveis_para(self, user):
        """Filtra demandas pela regra de visibilidade restrita (ADR 0049).
        Restritas só aparecem para: responsável, ADM, CG ou superuser.
        Centraliza a regra que antes vivia em `_filtrar_visiveis` (views).
        """
        q = _q_demanda_visivel_para(user)
        if q is None:
            return self
        return self.filter(q)


class DemandaManager(models.Manager.from_queryset(DemandaQuerySet)):
    pass


class Tema(models.Model):
    """Categoria/assunto de Demanda. Separado de pessoas.Tag por decisão de
    produto: tema mede 'do que se trata' (Saúde, Educação, Mobilidade);
    tag mede 'quem é' (Líder local, Microempresa). Ver ADR 0042."""

    nome = models.CharField("nome", max_length=50, unique=True)
    cor = models.CharField("cor", max_length=7, blank=True, help_text="Hex #RRGGBB")
    descricao = models.TextField("descrição", blank=True)
    ativo = models.BooleanField("ativo", default=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "tema"
        verbose_name_plural = "temas"
        ordering = ["nome"]
        indexes = [models.Index(fields=["ativo"])]

    def __str__(self):
        return self.nome


class Demanda(AuditavelMixin, models.Model):
    """Solicitação ou registro de ação política. Coração operacional."""

    ORIGEM_RESPONSIVA = "responsiva"
    ORIGEM_PROATIVA = "proativa"
    ORIGEM_CHOICES = [
        (ORIGEM_RESPONSIVA, "Responsiva"),
        (ORIGEM_PROATIVA, "Proativa"),
    ]

    CANAL_CHOICES = [
        ("dm_instagram", "DM Instagram"),
        ("whatsapp", "WhatsApp"),
        ("presencial", "Presencial"),
        ("telefone", "Telefone"),
        ("email", "E-mail"),
        ("oficio", "Ofício"),
        ("indicacao_interna", "Indicação interna"),
        ("redes_sociais", "Redes sociais"),
        ("outro", "Outro"),
    ]

    STATUS_NOVO = "novo"
    STATUS_EM_ANDAMENTO = "em_andamento"
    STATUS_AGUARDANDO_TERCEIROS = "aguardando_terceiros"
    STATUS_AGUARDANDO_PESSOA = "aguardando_pessoa"
    STATUS_CONCLUIDA = "concluida"
    STATUS_ARQUIVADO = "arquivado"
    STATUS_CHOICES = [
        (STATUS_NOVO, "Novo"),
        (STATUS_EM_ANDAMENTO, "Em andamento"),
        (STATUS_AGUARDANDO_TERCEIROS, "Aguardando terceiros"),
        (STATUS_AGUARDANDO_PESSOA, "Aguardando pessoa"),
        (STATUS_CONCLUIDA, "Concluída"),
        (STATUS_ARQUIVADO, "Arquivado"),
    ]

    RESULTADO_PENDENTE = "pendente"
    RESULTADO_ATENDIDO = "atendido"
    RESULTADO_ATENDIDO_PARCIALMENTE = "atendido_parcialmente"
    RESULTADO_NAO_ATENDIDO = "nao_atendido"
    RESULTADO_INVIAVEL = "inviavel"
    RESULTADO_NAO_SE_APLICA = "nao_se_aplica"
    RESULTADO_CHOICES = [
        (RESULTADO_PENDENTE, "Pendente"),
        (RESULTADO_ATENDIDO, "Atendido"),
        (RESULTADO_ATENDIDO_PARCIALMENTE, "Atendido parcialmente"),
        (RESULTADO_NAO_ATENDIDO, "Não atendido"),
        (RESULTADO_INVIAVEL, "Inviável"),
        (RESULTADO_NAO_SE_APLICA, "Não se aplica"),
    ]

    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("normal", "Normal"),
        ("alta", "Alta"),
        ("urgente", "Urgente"),
    ]

    COORDENACAO_GABINETE = "gabinete"
    COORDENACAO_JURIDICO = "juridico"
    COORDENACAO_COMUNICACAO = "comunicacao"
    COORDENACAO_CHOICES = [
        (COORDENACAO_GABINETE, "Gabinete"),
        (COORDENACAO_JURIDICO, "Jurídico"),
        (COORDENACAO_COMUNICACAO, "Comunicação"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField("número", max_length=20, unique=True, blank=True)
    slug_publico = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        editable=False,
        help_text="Slug curto (8 chars) para URLs públicas. Gerado automaticamente no save().",
    )
    titulo = models.CharField("título", max_length=200)
    descricao = models.TextField("descrição")
    origem = models.CharField(max_length=15, choices=ORIGEM_CHOICES, default=ORIGEM_RESPONSIVA)
    canal_entrada = models.CharField("canal de entrada", max_length=30, choices=CANAL_CHOICES)
    anonimo = models.BooleanField("anônima", default=False)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_NOVO)
    resultado = models.CharField(
        max_length=25, choices=RESULTADO_CHOICES, default=RESULTADO_PENDENTE
    )
    resultado_observacao = models.TextField("observação do resultado", blank=True, default="")
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default="normal")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="demandas_responsavel",
    )
    coordenacao_responsavel = models.CharField(
        "coordenação responsável", max_length=15, choices=COORDENACAO_CHOICES
    )
    restrito = models.BooleanField("restrita", default=False)
    prazo = models.DateField(null=True, blank=True)
    observacoes_arquivamento = models.TextField(
        "observações de arquivamento", blank=True, default=""
    )
    arquivado_em = models.DateTimeField("arquivada em", null=True, blank=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="demandas_criadas",
    )
    pessoas = models.ManyToManyField(
        "pessoas.Pessoa", through="DemandaPessoa", related_name="demandas"
    )
    entidades = models.ManyToManyField(
        "pessoas.Entidade", through="DemandaEntidade", related_name="demandas"
    )
    temas = models.ManyToManyField(Tema, blank=True, related_name="demandas")
    # GenericRelation permite acesso reverso (demanda.anexos.all()) e participa
    # do CASCADE quando a Demanda é deletada — anexos órfãos são removidos
    # automaticamente, sem depender do signal pre_delete (defesa em camadas).
    anexos = GenericRelation(
        "Anexo", content_type_field="content_type", object_id_field="object_id"
    )

    objects = DemandaManager()

    class Meta:
        verbose_name = "demanda"
        verbose_name_plural = "demandas"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["responsavel"]),
            models.Index(fields=["status"]),
            models.Index(fields=["resultado"]),
            models.Index(fields=["status", "coordenacao_responsavel"]),
            models.Index(fields=["responsavel", "status"]),
            models.Index(fields=["resultado", "criado_em"]),
            models.Index(fields=["criado_em"]),
            models.Index(fields=["prazo"]),
        ]
        permissions = [
            ("pode_arquivar_demanda", "Pode arquivar demanda concluída"),
            (
                "pode_arquivar_sem_responder",
                "Pode arquivar demanda não concluída (com justificativa)",
            ),
            ("pode_marcar_restrita", "Pode marcar/desmarcar demanda como restrita"),
            ("pode_atribuir_responsavel", "Pode atribuir/reatribuir responsável"),
            ("pode_reabrir_demanda", "Pode reabrir demanda concluída"),
            ("pode_excluir_demanda", "Pode excluir demanda definitivamente"),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Snapshot do estado original — usado em clean() e signal post_save
        # para detectar transições proibidas e disparar interações automáticas.
        self._original_status = self.status
        self._original_resultado = self.resultado
        self._original_responsavel_id = self.responsavel_id

    def __str__(self):
        return f"{self.numero or '(sem número)'} — {self.titulo}"

    def clean(self):
        super().clean()
        # Regra de fechamento bifurcada por origem (ADR 0043 / fluxos-de-estado.md §1.3)
        if self.status == self.STATUS_CONCLUIDA:
            if self.resultado == self.RESULTADO_PENDENTE:
                raise ValidationError(
                    {
                        "resultado": "Status 'concluida' exige resultado classificado (não pode ser 'pendente')."
                    }
                )
            if self.origem == self.ORIGEM_RESPONSIVA:
                # pk pode ser None em criações via form ainda não persistidas;
                # nesses casos não há interações vinculadas e a regra reprova.
                tem_devolutiva = (
                    self.pk
                    and self.interacoes.filter(
                        tipo=Interacao.TIPO_DEVOLUTIVA, status=Interacao.STATUS_REALIZADA
                    ).exists()
                )
                if not tem_devolutiva:
                    raise ValidationError(
                        {
                            "status": "Demanda responsiva só conclui com Interação de devolutiva registrada."
                        }
                    )
        # Arquivamento sem ter concluído exige justificativa
        if (
            self.status == self.STATUS_ARQUIVADO
            and self._original_status != self.STATUS_CONCLUIDA
            and not self.observacoes_arquivamento
        ):
            raise ValidationError(
                {
                    "status": "Arquivamento direto (sem ter concluído) exige observacoes_arquivamento."
                }
            )
        # Resultado uma vez classificado não volta a 'pendente'
        if (
            self._original_resultado
            and self._original_resultado != self.RESULTADO_PENDENTE
            and self.resultado == self.RESULTADO_PENDENTE
        ):
            raise ValidationError(
                {"resultado": "Resultado já classificado não pode voltar a 'pendente'."}
            )

    def save(self, *args, **kwargs):
        if self.status == self.STATUS_ARQUIVADO and not self.arquivado_em:
            self.arquivado_em = timezone.now()
        if self.numero and self.slug_publico:
            super().save(*args, **kwargs)
            return
        # Registro novo: gera número (D-AAMM-NNNNN) e slug_publico, tenta
        # INSERT em savepoint. Em colisão (UNIQUE de numero OU slug),
        # regenera o campo vazio/colidido até 10 vezes.
        # Padrão idêntico ao slug_publico de Pessoa/Entidade (ADR 0051).
        ultima_excecao = None
        for _ in range(10):
            if not self.numero:
                self.numero = self.gerar_numero()
            if not self.slug_publico:
                self.slug_publico = gerar_slug_publico()
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                return
            except IntegrityError as exc:
                ultima_excecao = exc
                # Regenera o campo que colidiu na próxima tentativa.
                msg = str(exc).lower()
                if "slug_publico" in msg:
                    self.slug_publico = ""
                if "numero" in msg or "slug_publico" not in msg:
                    self.numero = ""
                continue
        raise ultima_excecao  # 10 colisões consecutivas — improvável no espaço combinado

    @classmethod
    def gerar_numero(cls):
        """Formato D-AAMM-NNNNN (ADR 0056).

        - `AA` = ano em 2 dígitos, `MM` = mês em 2 dígitos (ordenação cronológica como string).
        - `NNNNN` = aleatório uniforme em [10000, 99999] (sempre 5 dígitos visualmente).
        Colisão é tratada no `save()` por retry em savepoint.
        """
        agora = timezone.now()
        sufixo = random.randint(10000, 99999)
        return f"D-{agora.strftime('%y%m')}-{sufixo}"

    def tem_partes(self):
        """Demanda não-anônima precisa ter ao menos uma parte vinculada."""
        return self.demanda_pessoas.exists() or self.demanda_entidades.exists()

    def pode_ser_visto_por(self, user):
        """Visibilidade segue ADR/permissoes.md §3.3 + edge case 5.1."""
        from core.permissoes import eh_cg_plus

        if not self.restrito:
            return True
        if self.responsavel_id == user.id:
            return True
        return eh_cg_plus(user)

    @classmethod
    def q_visivel_para(cls, user):
        """Q predicate de visibilidade — para uso em queries externas (como
        PessoaDetailView / EntidadeDetailView) que não passam pelo manager.
        Retorna None se CG+."""
        return _q_demanda_visivel_para(user)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("demandas:demanda_detalhe", kwargs={"slug": self.slug_publico})


class DemandaPessoa(models.Model):
    demanda = models.ForeignKey(Demanda, on_delete=models.CASCADE, related_name="demanda_pessoas")
    pessoa = models.ForeignKey(
        "pessoas.Pessoa", on_delete=models.PROTECT, related_name="demanda_pessoas"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "parte (pessoa)"
        verbose_name_plural = "partes (pessoas)"
        constraints = [
            models.UniqueConstraint(
                fields=["demanda", "pessoa"],
                name="demanda_pessoa_unica",
                violation_error_message="Esta pessoa já é parte desta demanda.",
            ),
        ]
        indexes = [
            models.Index(fields=["demanda"]),
            models.Index(fields=["pessoa"]),
        ]

    def __str__(self):
        return self.pessoa.nome_exibicao


class DemandaEntidade(models.Model):
    demanda = models.ForeignKey(Demanda, on_delete=models.CASCADE, related_name="demanda_entidades")
    entidade = models.ForeignKey(
        "pessoas.Entidade", on_delete=models.PROTECT, related_name="demanda_entidades"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "parte (entidade)"
        verbose_name_plural = "partes (entidades)"
        constraints = [
            models.UniqueConstraint(
                fields=["demanda", "entidade"],
                name="demanda_entidade_unica",
                violation_error_message="Esta entidade já é parte desta demanda.",
            ),
        ]
        indexes = [
            models.Index(fields=["demanda"]),
            models.Index(fields=["entidade"]),
        ]

    def __str__(self):
        return self.entidade.nome


class Interacao(models.Model):
    """Evento na timeline da demanda. Manual (assessor) ou automática (signal).

    Status `agendada` cobre futuro (data_ocorrencia > now); `realizada` é
    passado/presente; `cancelada` é histórico de algo que não vai acontecer.
    """

    TIPO_REGISTRO_INICIAL = "registro_inicial"
    TIPO_CONTATO_PESSOA = "contato_com_pessoa"
    TIPO_CONTATO_INTERNO = "contato_interno"
    TIPO_REUNIAO = "reuniao"
    TIPO_ENCAMINHAMENTO = "encaminhamento_externo"
    TIPO_RETORNO_EXTERNO = "retorno_externo_recebido"
    TIPO_DEVOLUTIVA = "devolutiva"
    TIPO_MUDANCA_STATUS = "mudanca_status"
    TIPO_MUDANCA_RESPONSAVEL = "mudanca_responsavel"
    TIPO_MUDANCA_RESULTADO = "mudanca_resultado"
    TIPO_ARQUIVAMENTO = "arquivamento"
    TIPO_ANOTACAO = "anotacao_interna"
    TIPO_CHOICES = [
        (TIPO_REGISTRO_INICIAL, "Registro inicial"),
        (TIPO_CONTATO_PESSOA, "Contato com pessoa"),
        (TIPO_CONTATO_INTERNO, "Contato interno"),
        (TIPO_REUNIAO, "Reunião"),
        (TIPO_ENCAMINHAMENTO, "Encaminhamento externo"),
        (TIPO_RETORNO_EXTERNO, "Retorno externo recebido"),
        (TIPO_DEVOLUTIVA, "Devolutiva ao demandante"),
        (TIPO_MUDANCA_STATUS, "Mudança de status"),
        (TIPO_MUDANCA_RESPONSAVEL, "Mudança de responsável"),
        (TIPO_MUDANCA_RESULTADO, "Mudança de resultado"),
        (TIPO_ARQUIVAMENTO, "Arquivamento"),
        (TIPO_ANOTACAO, "Anotação interna"),
    ]

    STATUS_REALIZADA = "realizada"
    STATUS_AGENDADA = "agendada"
    STATUS_CANCELADA = "cancelada"
    STATUS_CHOICES = [
        (STATUS_REALIZADA, "Realizada"),
        (STATUS_AGENDADA, "Agendada"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    JANELA_EDICAO_HORAS = 24

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    demanda = models.ForeignKey(Demanda, on_delete=models.CASCADE, related_name="interacoes")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="interacoes"
    )
    tipo = models.CharField(max_length=40, choices=TIPO_CHOICES)
    conteudo = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_REALIZADA)
    data_ocorrencia = models.DateTimeField()
    automatica = models.BooleanField(default=False)
    interacao_origem = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="follow_ups",
    )
    # FK opcional para Encaminhamento — populada quando a Interacao representa
    # um evento de um encaminhamento (envio ou resposta). Permite expansão
    # do item na timeline mostrando detalhes técnicos. Ver ADR 0045.
    encaminhamento = models.ForeignKey(
        "Encaminhamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interacoes",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "interação"
        verbose_name_plural = "interações"
        ordering = ["-data_ocorrencia"]
        indexes = [
            models.Index(fields=["demanda"]),
            models.Index(fields=["demanda", "-data_ocorrencia"]),
            models.Index(fields=["autor", "status", "data_ocorrencia"]),
            models.Index(fields=["status", "data_ocorrencia"]),
        ]
        permissions = [
            ("pode_editar_interacao_alheia", "Pode editar interação de outro autor"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} ({self.get_status_display()}) — {self.data_ocorrencia:%d/%m/%Y}"

    def pode_editar(self, user):
        """Janela de 24h para o autor; sempre OK para ADM/CG; nunca para automáticas."""
        from core.permissoes import eh_cg_plus

        if self.automatica:
            return False
        if eh_cg_plus(user):
            return True
        if self.autor_id == user.id:
            return (timezone.now() - self.criado_em) < timedelta(hours=self.JANELA_EDICAO_HORAS)
        return False

    @property
    def vencida(self):
        return self.status == self.STATUS_AGENDADA and self.data_ocorrencia < timezone.now()


class Encaminhamento(models.Model):
    """Comunicação enviada a órgão externo (ofício, requerimento, ligação)."""

    TIPO_DOCUMENTO_CHOICES = [
        ("oficio", "Ofício"),
        ("requerimento_informacao", "Requerimento de informação"),
        ("indicacao", "Indicação"),
        ("ligacao", "Ligação"),
        ("email", "E-mail"),
        ("presencial", "Presencial"),
        ("outro", "Outro"),
    ]

    STATUS_ENVIADO = "enviado"
    STATUS_PRAZO_VENCIDO = "prazo_vencido"
    STATUS_RESPONDIDO_SAT = "respondido_satisfatorio"
    STATUS_RESPONDIDO_INSAT = "respondido_insatisfatorio"
    STATUS_SEM_RESPOSTA = "sem_resposta"
    STATUS_CHOICES = [
        (STATUS_ENVIADO, "Enviado"),
        (STATUS_PRAZO_VENCIDO, "Prazo vencido"),
        (STATUS_RESPONDIDO_SAT, "Respondido (satisfatório)"),
        (STATUS_RESPONDIDO_INSAT, "Respondido (insatisfatório)"),
        (STATUS_SEM_RESPOSTA, "Sem resposta"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    demanda = models.ForeignKey(Demanda, on_delete=models.CASCADE, related_name="encaminhamentos")
    destinatario_orgao = models.CharField("órgão destinatário", max_length=200)
    destinatario_pessoa = models.CharField(
        "pessoa destinatária", max_length=200, blank=True, default=""
    )
    tipo_documento = models.CharField(max_length=40, choices=TIPO_DOCUMENTO_CHOICES)
    numero_documento = models.CharField(max_length=50, blank=True, default="")
    data_envio = models.DateField()
    prazo_resposta = models.DateField(null=True, blank=True)
    data_resposta = models.DateField(null=True, blank=True)
    conteudo_resposta = models.TextField(blank=True, default="")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_ENVIADO)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="encaminhamentos_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    anexos = GenericRelation(
        "Anexo", content_type_field="content_type", object_id_field="object_id"
    )

    class Meta:
        verbose_name = "encaminhamento"
        verbose_name_plural = "encaminhamentos"
        ordering = ["-data_envio"]
        indexes = [
            models.Index(fields=["demanda"]),
            models.Index(fields=["destinatario_orgao"]),
            models.Index(fields=["prazo_resposta", "status"]),
        ]
        permissions = [
            ("pode_excluir_encaminhamento", "Pode excluir encaminhamento"),
        ]

    def __str__(self):
        return f"{self.get_tipo_documento_display()} → {self.destinatario_orgao} ({self.data_envio:%d/%m/%Y})"

    def clean(self):
        super().clean()
        # Para mover para respondido_*: data_resposta e conteudo_resposta obrigatórios.
        if self.status in (self.STATUS_RESPONDIDO_SAT, self.STATUS_RESPONDIDO_INSAT):
            if not self.data_resposta or not self.conteudo_resposta:
                raise ValidationError(
                    "Para registrar resposta é preciso preencher data e conteúdo."
                )

    @property
    def prazo_vencido_hoje(self):
        return (
            self.status == self.STATUS_ENVIADO
            and self.prazo_resposta is not None
            and self.prazo_resposta < timezone.now().date()
        )


class Anexo(models.Model):
    """Arquivo polimórfico — pode ser pendurado em qualquer model registrado.

    MVP cobre Demanda, Pessoa, Entidade e Encaminhamento. Limpeza de órfãos
    via signal pre_delete nos modelos pais (ver demandas/signals.py).
    """

    TAMANHO_MAXIMO_BYTES = 25 * 1024 * 1024  # 25 MB
    # Whitelist de MIMEs removida (ADR 0056) — anexo aceita qualquer arquivo
    # até TAMANHO_MAXIMO_BYTES. A defesa anti-XSS é feita na entrega via
    # `AnexoDownloadView`: Content-Disposition: attachment força o browser a
    # baixar (não executar/exibir inline), e X-Content-Type-Options: nosniff
    # impede o browser de "adivinhar" um tipo executável. Em produção, o
    # Nginx deve estar configurado com os mesmos headers para /media/.

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    objeto_pai = GenericForeignKey("content_type", "object_id")

    arquivo = models.FileField(upload_to="anexos/%Y/%m/")
    nome_original = models.CharField(max_length=255)
    tamanho_bytes = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, default="")
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="anexos_enviados",
    )
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "anexo"
        verbose_name_plural = "anexos"
        ordering = ["-enviado_em"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return self.nome_original

    def clean(self):
        super().clean()
        if self.tamanho_bytes and self.tamanho_bytes > self.TAMANHO_MAXIMO_BYTES:
            raise ValidationError(
                {
                    "arquivo": f"Arquivo excede o limite de {self.TAMANHO_MAXIMO_BYTES // (1024*1024)} MB."
                }
            )


class ItemInbox(models.Model):
    """Captura rápida GTD. UX completa em Fase 4 — Fase 3 só cria o modelo."""

    STATUS_PENDENTE = "pendente"
    STATUS_PROCESSADO = "processado"
    STATUS_DESCARTADO = "descartado"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_PROCESSADO, "Processado"),
        (STATUS_DESCARTADO, "Descartado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conteudo = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="itens_inbox"
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    demanda_gerada = models.ForeignKey(
        Demanda, on_delete=models.SET_NULL, null=True, blank=True, related_name="itens_inbox"
    )
    motivo_descarte = models.TextField(blank=True, default="")
    processado_em = models.DateTimeField(null=True, blank=True)
    processado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="itens_processados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "item de inbox"
        verbose_name_plural = "itens de inbox"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["status", "criado_em"]),
            models.Index(fields=["autor"]),
        ]

    def __str__(self):
        return f"{self.get_status_display()}: {self.conteudo[:60]}"

    def clean(self):
        super().clean()
        if self.status == self.STATUS_PROCESSADO and not self.demanda_gerada_id:
            raise ValidationError(
                {"demanda_gerada": "Item processado deve ter demanda_gerada preenchida."}
            )
        if self.status == self.STATUS_DESCARTADO and not self.motivo_descarte:
            raise ValidationError(
                {"motivo_descarte": "Item descartado deve ter motivo preenchido."}
            )
