# MPD — Fluxos de Estado

Documento das regras de transição de estado das entidades operacionais do sistema. Define o que pode virar o quê, sob quais condições, com quais consequências automáticas.

> **Princípio:** transições de estado são o esqueleto da operação. Quando uma transição é proibida no nível do model, ela é proibida em qualquer porta de entrada (formulário, admin, API, comando, importação). É essa garantia que sustenta a "regra de ouro" do sistema: **caso só fecha com retorno documentado e resultado classificado**.

---

## 1. Caso — Diagrama de estados

```
                  ┌──────────────────┐
                  │      novo        │
                  └────────┬─────────┘
                           │ (assessor começa a trabalhar)
                           ▼
                  ┌──────────────────┐
        ┌────────►│  em_andamento    │
        │         └─┬─────────┬──────┘
        │           │         │
        │ (volta a  │         │ (depende de terceiro)
        │  ser ação │         ▼
        │  do mand.)│   ┌─────────────────────┐
        │           │   │ aguardando_terceiros│
        │           │   └──┬──────────────────┘
        │           │      │
        │           │      │ (resposta recebida)
        │           ▼      │
        │  ┌───────────────────────┐
        └──┤  aguardando_cidadao   │
           └───────────┬───────────┘
                       │ (resposta dada ao cidadão, com data e conteúdo)
                       ▼
                  ┌──────────────────┐
                  │   respondido     │◄─── ⚠ EXIGE retorno_data + retorno_conteudo
                  └────────┬─────────┘     E resultado ≠ 'pendente'
                           │ (encerramento administrativo)
                           ▼
                  ┌──────────────────┐
                  │   arquivado      │
                  └──────────────────┘

  ⚠ Atalho excepcional (com justificativa obrigatória):
     novo / em_andamento / aguardando_* ──► arquivado
     (apenas CG ou ADM, com observacoes_arquivamento preenchido)
```

### 1.1 Estados

| Estado | Significado | Quem pode mover daqui |
|---|---|---|
| `novo` | Caso recém-criado, sem trabalho iniciado. | Qualquer usuário com permissão de editar o caso. |
| `em_andamento` | Equipe está trabalhando ativamente. | Qualquer usuário com permissão. |
| `aguardando_terceiros` | Encaminhamento foi feito; aguarda resposta de órgão externo. | Qualquer usuário com permissão. |
| `aguardando_cidadao` | Mandato precisa de informação adicional do cidadão. | Qualquer usuário com permissão. |
| `respondido` | Cidadão recebeu retorno e resultado foi classificado. | CO, CG, ADM. |
| `arquivado` | Encerrado e fora do fluxo ativo. | CG, ADM. |

### 1.2 Transições permitidas

| De ↓ \ Para → | novo | em_andamento | aguard_terc | aguard_cid | respondido | arquivado |
|---|---|---|---|---|---|---|
| **novo** | — | ✅ | ✅ | ✅ | ✅* | ⚠ (com justif.) |
| **em_andamento** | ❌ | — | ✅ | ✅ | ✅* | ⚠ (com justif.) |
| **aguard_terceiros** | ❌ | ✅ | — | ✅ | ✅* | ⚠ (com justif.) |
| **aguard_cidadao** | ❌ | ✅ | ✅ | — | ✅* | ⚠ (com justif.) |
| **respondido** | ❌ | ✅ (reabertura) | ❌ | ❌ | — | ✅ |
| **arquivado** | ❌ | ❌ | ❌ | ❌ | ❌ | — |

*Com `retorno_data`, `retorno_conteudo` obrigatoriamente preenchidos **e** `resultado` diferente de `pendente`.

### 1.3 Regras codificadas

**No `clean()` do model `Caso`:**

```python
def clean(self):
    if self.status == 'respondido':
        if not self.retorno_data or not self.retorno_conteudo:
            raise ValidationError({
                'status': "Status 'respondido' exige retorno_data e retorno_conteudo preenchidos."
            })
        if self.resultado == 'pendente':
            raise ValidationError({
                'resultado': "Status 'respondido' exige resultado classificado (não pode ser 'pendente')."
            })

    if self.status == 'arquivado':
        # Permitido se está vindo de 'respondido' (caminho normal)
        # OU se tem observacoes_arquivamento (atalho com justificativa)
        if self._original_status != 'respondido' and not self.observacoes_arquivamento:
            raise ValidationError({
                'status': "Arquivamento direto (sem ter respondido) exige observacoes_arquivamento."
            })

    # Reabertura de respondido
    if self._original_status == 'respondido' and self.status == 'em_andamento':
        # Permitido. Limpa retorno para forçar novo preenchimento ao reencerrar.
        # Decisão registrada como interação automática.
        # Resultado é mantido (pode ser revisado ao reencerrar).
        pass
```

**Mecanismo `_original_status`:** model carrega o status original ao ser inicializado e compara com o atual no `clean()`. Implementado via override de `__init__` ou `from_db`.

### 1.4 Consequências automáticas (signals)

Toda mudança de status do caso gera uma **interação automática** (tipo `mudanca_status`) registrada na timeline:

```python
@receiver(post_save, sender=Caso)
def registrar_mudanca_status(sender, instance, created, **kwargs):
    if created:
        Interacao.objects.create(
            caso=instance,
            autor=instance.criado_por,
            tipo='registro_inicial',
            conteudo=f"Caso aberto: {instance.titulo}",
            status='realizada',
            data_ocorrencia=instance.criado_em,
            automatica=True,
        )
        return

    if instance._original_status != instance.status:
        Interacao.objects.create(
            caso=instance,
            autor=_get_current_user(),  # via middleware
            tipo='mudanca_status',
            conteudo=f"Status: {instance._original_status} → {instance.status}",
            status='realizada',
            data_ocorrencia=timezone.now(),
            automatica=True,
        )

    if instance._original_responsavel_id != instance.responsavel_id:
        # idem para mudança de responsável

    if instance._original_resultado != instance.resultado:
        # idem para mudança de resultado (tipo='mudanca_resultado')
```

**Implicação importante:** a timeline do caso contém tanto interações manuais (registradas pelos assessores) quanto automáticas (geradas pelo sistema). Distinguidas visualmente por flag `automatica=TRUE` e categoria visual diferente.

### 1.5 Mudança de responsável

Mesma lógica: signal detecta mudança em `responsavel_id` e gera interação automática `mudanca_responsavel` na timeline.

```
"Responsável: [não atribuído] → Maria Silva"
"Responsável: Maria Silva → João Pereira"
```

Quando o assessor responsável é desativado (`is_active=FALSE`), o caso aparece em listagens com badge de alerta "responsável inativo" — sinal para reatribuir, mas não muda automaticamente.

### 1.6 Reabertura de caso respondido

Cenário: caso foi marcado como `respondido`, mas o cidadão volta dizendo que a resposta foi insuficiente, ou descobre-se algo novo.

**Decisão:** permitir reabertura, com regras:

1. Apenas CG e ADM podem reabrir (mover de `respondido` → `em_andamento`).
2. Reabertura **NÃO** apaga `retorno_data` e `retorno_conteudo` — eles ficam como histórico do retorno anterior.
3. Quando o caso for novamente movido para `respondido`, exige preenchimento de novo retorno (sobrescrevendo).
4. A reabertura gera interação automática `mudanca_status` na timeline.

Alternativa considerada e descartada: criar um novo caso vinculado ao anterior. Mais "limpo" tecnicamente, mas operacionalmente quebra a noção de continuidade do relacionamento. Opção pode reaparecer em v2.x se a complexidade justificar.

---

## 2. Caso — Resultado (dimensão independente do status)

`status` mede em que ponto do ciclo o caso está. `resultado` mede o desfecho material da demanda — se vingou, se não vingou, se nem se aplicava. As duas dimensões são independentes mas se cruzam na regra de fechamento.

### 2.1 Os seis valores

```
        ┌────────────────────────────────────────────────────────┐
        │  pendente  (default — ainda não há desfecho conhecido) │
        └────────────────────────────────────────────────────────┘
                              │
                              │ (assessor classifica conforme andamento)
                              ▼
        ┌──────────────┬───────────────────┬──────────────┐
        │  atendido    │     atendido_     │ nao_atendido │
        │              │   parcialmente    │              │
        └──────────────┴───────────────────┴──────────────┘
        ┌──────────────┬───────────────────┐
        │   inviavel   │   nao_se_aplica   │
        └──────────────┴───────────────────┘
```

| Valor | Significado |
|---|---|
| `pendente` | Default. Ainda não há desfecho conhecido. Caso pode estar em qualquer status; só não pode estar em `respondido` (regra de fechamento). |
| `atendido` | Demanda foi resolvida. Cidadão obteve o que pediu. |
| `atendido_parcialmente` | Demanda foi parcialmente resolvida. Conseguimos parte do que se pedia. |
| `nao_atendido` | Tentativa frustrada. Tentou-se resolver mas não vingou (negativa de terceiro, falta de recurso, inviabilidade superveniente). |
| `inviavel` | Ao analisar, mostrou-se impossível atender (fora de competência municipal, juridicamente impossível, contradiz lei superior). Distingue de `nao_atendido`: nem se tentou porque não cabia. |
| `nao_se_aplica` | A categoria de avaliação não cabe neste caso. Reservado a casos proativos sem dimensão de "atendimento" — postagens, discursos por convicção política, manifestações públicas, etc. |

### 2.2 Independência do status

`resultado` pode ser atualizado **a qualquer momento da vida do caso**, em qualquer status. O assessor pode marcar `atendido` antes mesmo de comunicar o cidadão (porque às vezes a obra sai antes da gente avisar). Isso gera uma fila operacional valiosa: "casos com resultado conhecido mas sem retorno comunicado", visível no dashboard.

### 2.3 Regra de fechamento (cruzamento entre status e resultado)

Para `status` ir para `respondido`, `resultado` precisa estar classificado (qualquer valor exceto `pendente`). Codificado no `clean()` (ver seção 1.3).

Matriz de validade ao tentar fechar (status → respondido):

| `resultado` no momento | Pode fechar? |
|---|---|
| `pendente` | ❌ Bloqueado. Sistema exige classificação. |
| `atendido` | ✅ |
| `atendido_parcialmente` | ✅ |
| `nao_atendido` | ✅ |
| `inviavel` | ✅ |
| `nao_se_aplica` | ✅ |

### 2.4 Transições do resultado

| De ↓ \ Para → | pendente | atendido | parcial | nao_atend | inviavel | nao_se_apl |
|---|---|---|---|---|---|---|
| **pendente** | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| **atendido** | ❌ | — | ✅ | ✅ | ✅ | ✅ |
| **atendido_parcialmente** | ❌ | ✅ | — | ✅ | ✅ | ✅ |
| **nao_atendido** | ❌ | ✅ | ✅ | — | ✅ | ✅ |
| **inviavel** | ❌ | ✅ | ✅ | ✅ | — | ✅ |
| **nao_se_aplica** | ❌ | ✅ | ✅ | ✅ | ✅ | — |

**Regras:**

- Uma vez classificado, `resultado` não volta a `pendente`. Reclassificações entre os outros valores são livres (cenário típico: caso parecia atendido, mas surgiu problema → vira `atendido_parcialmente`).
- Cada mudança de `resultado` gera uma interação automática na timeline (tipo `mudanca_resultado`), com `automatica=TRUE`. Isso preserva o histórico de avaliações sucessivas.
- Quem pode mudar resultado: mesmas pessoas que podem editar o caso (ver `permissoes.md`).

### 2.5 Cenário de uso indevido e mitigação

`nao_se_aplica` pode ser usado como atalho para evitar dizer "não foi atendido". Mitigações leves, sem regra técnica dura:

1. Na UI, `nao_se_aplica` aparece por último no select, separado visualmente. Não é a opção que cai sob o cursor.
2. Painel de análise (Fase 5) mostra distribuição de `resultado` segregada por `origem`: se 80% dos casos responsivos terminam como `nao_se_aplica`, isso revela problema de uso. Visibilidade gerencial corrige sem precisar de regra rígida.

Se o problema aparecer no uso real, restringe-se depois (por exemplo: `nao_se_aplica` só pode ser escolhido em casos com `origem='proativa'`). Por enquanto, simplicidade.

### 2.6 Por que esta dimensão importa

A separação entre `status='respondido'` (cumprimos nosso dever de retorno) e `resultado='atendido'` (a demanda deu resultado) é a base para perguntas politicamente decisivas que o sistema vai responder:

- Quais bairros têm casos majoritariamente atendidos vs não-atendidos?
- Qual o índice de efetividade por tema, por canal, por coordenação?
- Quais cidadãos viram o mandato resolver algo concreto na vida deles? (Lista política central do sistema.)
- Qual a evolução temporal da efetividade do mandato?

Sem essa dimensão, o sistema sabe que respondeu — mas não sabe se entregou.

---

## 3. Interação — Diagrama de estados

```
                  ┌──────────────────┐
                  │     agendada     │  (data_ocorrencia futura)
                  └─┬─────────────┬──┘
                    │             │
       (chegou data │             │ (decidiu não fazer)
        ou execução)│             │
                    ▼             ▼
            ┌──────────────┐  ┌────────────┐
            │  realizada   │  │ cancelada  │
            └──────────────┘  └────────────┘
                    │
            (correção em até 24h pelo autor;
             após isso, imutável exceto ADM/CG)
```

### 3.1 Estados

| Estado | Significado |
|---|---|
| `realizada` | Aconteceu (passado). Default ao registrar evento histórico. |
| `agendada` | Ainda não aconteceu. `data_ocorrencia` no futuro. |
| `cancelada` | Foi agendada mas não vai acontecer. Mantida para histórico. |

### 3.2 Transições

| De ↓ \ Para → | realizada | agendada | cancelada |
|---|---|---|---|
| **(criação)** | ✅ (passado) | ✅ (futuro) | ❌ |
| **realizada** | — | ❌ | ❌ |
| **agendada** | ✅ (executada) | — | ✅ (desistida) |
| **cancelada** | ❌ | ❌ | — |

**Regra:** uma vez `realizada`, fica imutável (ressalva da janela de 24h para correção pelo autor). Uma vez `cancelada`, não volta.

### 3.3 Janela de edição de 24h

Após criação como `realizada`, o autor pode editar `conteudo` e `tipo` por 24h. Implementação:

```python
def pode_editar(self, user):
    if user.is_superuser or user.groups.filter(name__in=['Administrador', 'Chefe de Gabinete']).exists():
        return True
    if self.autor_id == user.id and (timezone.now() - self.criado_em) < timedelta(hours=24):
        return True
    return False
```

### 3.4 Interações automáticas — imutabilidade absoluta

Interações com `automatica=TRUE` (geradas por mudanças no caso) **nunca são editáveis nem canceláveis** por nenhum perfil. São o registro objetivo do que o sistema fez.

### 3.5 Schedule Follow-up

Ao salvar uma interação como `realizada`, formulário oferece checkbox "Criar follow-up". Se marcado, o usuário preenche tipo, data futura, conteúdo. Sistema cria nova interação:

```python
nova_interacao = Interacao.objects.create(
    caso=interacao_origem.caso,
    autor=interacao_origem.autor,
    tipo=tipo_followup,
    conteudo=conteudo_followup,
    status='agendada',
    data_ocorrencia=data_futura,
    interacao_origem_id=interacao_origem.id,  # ← liga à origem
)
```

Isso permite reconstruir cadeias: "essa ligação de hoje foi follow-up daquela reunião de 15 dias atrás, que foi follow-up do registro inicial do caso".

### 3.6 Interação agendada vence

Quando `data_ocorrencia` passa e `status` segue `agendada`, a interação é considerada **vencida**. Não há transição automática (sistema não muda de estado sozinho); apenas marcação visual:

- Aparece em "Minhas Interações Pendentes" com badge vermelho.
- Aparece no detalhe do caso destacada.
- Conta no painel do Chefe de Gabinete como "interações vencidas".

A não-transição automática é decisão deliberada: o autor precisa ativamente decidir se a interação foi feita (marca como `realizada`, possivelmente atualizando data e conteúdo) ou desistida (`cancelada`). Sistema não toma essa decisão por ele.

---

## 4. Item de Inbox — Diagrama de estados

```
              ┌──────────────┐
              │   pendente   │
              └──┬───────────┬┘
                 │           │
       (triagem) │           │ (descartado)
                 ▼           ▼
       ┌──────────────┐  ┌──────────────┐
       │ processado   │  │ descartado   │
       │ (gerou caso) │  │ (com motivo) │
       └──────────────┘  └──────────────┘
```

### 4.1 Estados

| Estado | Significado |
|---|---|
| `pendente` | Capturado, aguardando triagem. |
| `processado` | Triador converteu em caso. `caso_gerado_id` preenchido. |
| `descartado` | Triador decidiu que não vira caso. Motivo obrigatório. |

### 4.2 Transições

Estados terminais. Item processado ou descartado não volta a pendente.

| De ↓ \ Para → | pendente | processado | descartado |
|---|---|---|---|
| **(criação)** | ✅ | ❌ | ❌ |
| **pendente** | — | ✅ | ✅ |
| **processado** | ❌ | — | ❌ |
| **descartado** | ❌ | ❌ | — |

### 4.3 Regras codificadas

```python
def clean(self):
    if self.status == 'processado' and not self.caso_gerado_id:
        raise ValidationError("Item processado deve ter caso_gerado_id preenchido.")
    if self.status == 'descartado' and not self.motivo_descarte:
        raise ValidationError("Item descartado deve ter motivo_descarte preenchido.")
```

### 4.4 Item pendente envelhece

Como interação agendada, item pendente há muito tempo recebe destaque visual:

- Pendente há +7 dias: badge laranja na lista.
- Pendente há +30 dias: badge vermelho.

Não há transição automática. Pendência é responsabilidade humana de processar.

---

## 5. Encaminhamento — Diagrama de estados

```
              ┌──────────────┐
              │    enviado   │
              └──┬───────────┬┘
                 │           │
       (resposta)│           │(prazo passou sem resposta)
                 ▼           ▼
       ┌────────────────┐  ┌────────────────┐
       │ respondido_*   │  │ prazo_vencido  │
       │ (satisfatório  │  │                │
       │  ou não)       │  │                │
       └────────────────┘  └─┬──────────────┘
                             │
                  (eventualmente recebe resposta)
                             ▼
                    ┌────────────────┐
                    │ respondido_*   │
                    └────────────────┘

                    ┌────────────────┐
                    │  sem_resposta  │ (encerramento manual sem resposta)
                    └────────────────┘
```

### 5.1 Estados

| Estado | Significado |
|---|---|
| `enviado` | Encaminhado, aguardando resposta. |
| `prazo_vencido` | Prazo de resposta passou sem retorno. Marcação automática se houver `prazo_resposta`. |
| `respondido_satisfatorio` | Resposta recebida e atendeu à demanda. |
| `respondido_insatisfatorio` | Resposta recebida mas não atendeu. |
| `sem_resposta` | Encerrado manualmente sem ter recebido resposta (encerramento por desistência). |

### 5.2 Transições

| De ↓ \ Para → | enviado | prazo_venc | resp_sat | resp_insat | sem_resp |
|---|---|---|---|---|---|
| **enviado** | — | ✅ (auto) | ✅ | ✅ | ✅ |
| **prazo_vencido** | ❌ | — | ✅ | ✅ | ✅ |
| **respondido_***  | ❌ | ❌ | — | — | ❌ |
| **sem_resposta** | ❌ | ❌ | ❌ | ❌ | — |

### 5.3 Regras codificadas

- Para mover para `respondido_*`: `data_resposta` e `conteudo_resposta` obrigatórios.
- Transição `enviado` → `prazo_vencido` é automática (cron diário ou consulta ao consultar): se `prazo_resposta < hoje` e `status = 'enviado'`, marcar como `prazo_vencido`.

Implementação simples sem cron: campo é calculado dinamicamente nas queries. Mas para clareza no UI, vale ter campo `status` real e job diário que atualiza. Decisão de implementação fica para Fase 3.

### 5.4 Resposta recebida do órgão externo

Quando o assessor registra a resposta recebida:

```python
encaminhamento.data_resposta = date.today()
encaminhamento.conteudo_resposta = "Sesa informou que a obra está prevista para Q3"
encaminhamento.status = 'respondido_satisfatorio'  # ou insatisfatorio
encaminhamento.save()

# Cria interação no caso registrando o evento
Interacao.objects.create(
    caso=encaminhamento.caso,
    autor=request.user,
    tipo='retorno_externo_recebido',
    conteudo=f"Resposta de {encaminhamento.destinatario_orgao}: {encaminhamento.conteudo_resposta}",
    status='realizada',
    data_ocorrencia=timezone.now(),
)
```

Note que aqui é interação `manual`, não automática — porque foi o assessor que decidiu registrar e formatar.

---

## 6. Solicitação LGPD — Diagrama de estados

```
              ┌──────────────┐
              │   pendente   │
              └────┬─────────┘
                   │ (responsável começa a tratar)
                   ▼
              ┌──────────────┐
              │ em_analise   │
              └──┬───────────┬┘
                 │           │
       (atende)  │           │  (nega)
                 ▼           ▼
       ┌────────────────┐  ┌────────────────┐
       │   atendido     │  │     negado     │
       └────────────────┘  └────────────────┘
```

Estados terminais. Não permitem retorno. Regras simples — todas as transições são manuais e requerem perfil CO/CG/ADM com função LGPD.

---

## 7. Validação contínua

**Toda transição de estado:**

1. Passa pelo `clean()` do model.
2. Gera entrada em `auditlog_logentry`.
3. Em casos específicos (Caso), gera interação automática.
4. Recalcula campos derivados se aplicável (ex: `arquivado_em` quando status muda para `arquivado`).

**Defesa em profundidade:** mesmo que alguém edite via Django Admin ou shell Python, o `clean()` é chamado. Mesmo que pulem o `clean()`, o `save()` chama `full_clean()` por convenção. Mesmo que pulem isso, signals registram a mudança. É difícil quebrar a integridade sem ser intencional.

---

## 8. Comandos de manutenção

Comandos `manage.py` que operam sobre estados:

- `python manage.py atualizar_prazos_vencidos` — varre encaminhamentos `enviado` com `prazo_resposta` passado e marca como `prazo_vencido`. Roda diariamente via cron em produção.
- `python manage.py verificar_integridade` — busca anomalias: casos `respondido` sem `retorno_data` (não deveria existir, mas defesa contra dados corrompidos), interações `agendadas` há mais de 6 meses sem ação, etc.

---

*Documento atualizado quando regras de transição mudam. Versão atual: planejamento, pré-Fase 0.*
