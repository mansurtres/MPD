# MPD — Modelo de Dados

Schema do banco de dados do MPD. Foco em mínimo viável: apenas tabelas, campos e índices que o sistema realmente usa. Crescer quando justificado.

> **Convenção de leitura:** campos com `*` são obrigatórios (NOT NULL). `🔑` chave primária. `🔗` chave estrangeira. `🔒` único. Tipos seguem PostgreSQL.

> **PK:** todos os modelos usam `BIGSERIAL` (default Django via `BigAutoField`). Ver ADR 0025.

---

## 1. Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│   usuarios ──── auth_groups (Django padrão)                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│   pessoas ──┬── telefones (1:N — celular/fixo, eh_whatsapp) │
│             ├── emails (1:N)                                │
│             ├── redes_sociais (1:N — instagram/fb/li/x/...) │
│             ├── tags (M:N)                                  │
│             └── vinculos ──── entidades ── tags (M:N)       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│   demandas ──┬── demanda_pessoas (M:N → pessoas)            │
│              ├── demanda_entidades (M:N → entidades)        │
│              ├── interacoes (status: realizada/agendada/...)│
│              ├── encaminhamentos                            │
│              ├── anexos (polimórficos)                      │
│              └── tags (M:N — etiquetas livres)             │
│                                                             │
│   itens_inbox ──── (FK opcional para demandas)              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│   solicitacoes_lgpd                                         │
│   logs (gerenciado por django-auditlog)                     │
│   anexos (polimórficos — se vinculam a qualquer entidade)   │
└─────────────────────────────────────────────────────────────┘
```

**Total:** 16 tabelas próprias (incluindo `pessoas_telefone`, `pessoas_email`, `pessoas_redesocial`) + tabelas associativas M:N criadas pelo Django automaticamente + tabela de auditoria gerenciada pela biblioteca.

---

## 2. Decisões estruturantes

**Sem `tenant_id`.** Single-tenant no MVP. Multi-tenant é decisão para v2.x.

**Endereço inline em `pessoas` e `entidades`.** Um endereço por pessoa/entidade no MVP. Refatorar quando precisar de múltiplos.

**Tabela `tags` única, compartilhada** entre pessoas, entidades e demandas. Etiqueta livre, sem hierarquia (ver ADR 0039).

**Tema da demanda é uma tag** (sem categoria fixa). Critério de "qual tag pode ser tema" será definido na ADR de implementação da Demanda (Fase 3).

**Auditoria via `django-auditlog`.** Não modelamos tabela própria.

**Quatro perfis:** Administrador, Chefe de Gabinete, Coordenador, Assessor.

**Visibilidade por boolean `restrito`.** Demanda restrita é visível apenas para responsável, chefia e admin.

**Interação pode existir no futuro** (`status='agendada'`). É essa a infraestrutura que garante que demandas não se percam: cada interação encerrada pode gerar a próxima como agendada.

**Mudanças de status, responsável ou resultado da demanda geram interações automáticas** (tipo `mudanca_status`, `mudanca_responsavel`, `mudanca_resultado`, `arquivamento`). Histórico vira parte da timeline natural, sem tabela de auditoria contextual separada.

**Status e Resultado são dimensões independentes da Demanda.** `status` mede o ciclo do trabalho (`novo`, `em_andamento`, `concluida` etc.); `resultado` mede o desfecho material da demanda (`atendido`, `nao_atendido`, etc.). A regra de ouro do fechamento (ADR 0043): demanda **responsiva** só vai a `concluida` com Interação `devolutiva` registrada **e** resultado classificado; demanda **proativa** só exige resultado classificado.

**M:N entre Demanda e Partes.** Uma demanda pode ter múltiplas pessoas e entidades vinculadas. A FK simples (um cidadão, uma entidade) foi substituída por tabelas de junção `demanda_pessoas` e `demanda_entidades`, cada uma com campo `papel`. A constraint "pelo menos uma parte ou anônimo" é validada no formulário/view antes de persistir.

**Anexos polimórficos.** A tabela `anexos` usa `GenericForeignKey` do Django (via `django.contrib.contenttypes`) e pode ser vinculada a qualquer entidade do sistema: `Demanda`, `Pessoa`, `Entidade`, `Encaminhamento`. Sem FK de banco real — integridade garantida via signal `pre_delete`.

---

## 3. Tabela: `usuarios`

Custom user estendendo `AbstractUser` do Django.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| 🔒 `email` * | VARCHAR(254) | NOT NULL, UNIQUE | Login por email |
| 🔒 `username` * | VARCHAR(150) | NOT NULL, UNIQUE | Auto-derivado do email se não fornecido |
| `nome_completo` * | VARCHAR(200) | NOT NULL | |
| `cargo` | VARCHAR(100) | NULL | Texto livre. Ex: "Assessor Parlamentar" |
| `password` * | VARCHAR(128) | NOT NULL | Hashed |
| `is_active` * | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `is_staff` * | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| `is_superuser` * | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| `last_login` | TIMESTAMP | NULL | |
| `date_joined` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Índices:** `email`, `username`, `is_active`.

**Perfis (Groups):** quatro grupos via data migration na Fase 1: `Administrador`, `Chefe de Gabinete`, `Coordenador`, `Assessor`. Cada usuário pertence a exatamente um grupo (regra de aplicação).

**Distinção Coordenador Jurídico vs Comunicação:** dada pela `coordenacao_responsavel` que assumem nas demandas, não por grupos diferentes.

---

## 4. Tabela: `pessoas`

Núcleo do sistema. Endereço inline.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| `nome` * | VARCHAR(100) | NOT NULL | |
| `sobrenome` * | VARCHAR(150) | NOT NULL | |
| `nome_social` | VARCHAR(200) | NULL | Tem prioridade na exibição |
| 🔒 `cpf` | VARCHAR(14) | UNIQUE NULLS DISTINCT | Validado por algoritmo |
| `data_nascimento` | DATE | NULL | |
| `genero` | VARCHAR(30) | NULL | CHECK IN ('mulher','homem','nao_binario','outro','prefere_nao_dizer') |
| `cep` | VARCHAR(9) | NULL | |
| `logradouro` | VARCHAR(200) | NULL | |
| `numero` | VARCHAR(20) | NULL | |
| `complemento` | VARCHAR(100) | NULL | |
| `bairro` * | VARCHAR(100) | NOT NULL | |
| `cidade` * | VARCHAR(100) | NOT NULL | |
| `estado` * | VARCHAR(2) | NOT NULL, DEFAULT 'ES' | |
| `observacoes` | TEXT | NULL | |
| `origem_cadastro` * | VARCHAR(20) | NOT NULL | CHECK IN ('manual','inbox','importacao') |
| `ativo` * | BOOLEAN | NOT NULL, DEFAULT TRUE | Soft delete |
| `anonimizado` * | BOOLEAN | NOT NULL, DEFAULT FALSE | Por LGPD |
| 🔗 `criado_por_id` * | UUID | FK → usuarios(id) | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| `atualizado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Constraint de aplicação** (validada na view, não no model — depende dos formsets):

Pelo menos um canal de contato cadastrado: ao menos um `Telefone` em `pessoas_telefone` (§4.1), ou um `EmailPessoa` em `pessoas_email` (§4.2), ou um `RedeSocial` em `pessoas_redesocial` (§4.3). Ver ADR 0037.

**Índices:**
- `email`, `cpf` (busca e deduplicação)
- `(nome, sobrenome)` composto
- `bairro`, `(ativo)`
- GIN em `to_tsvector('portuguese', nome || ' ' || sobrenome || ' ' || COALESCE(nome_social, ''))` para busca full-text

**Anonimização (LGPD):** `nome` vira `'[Pessoa Removida]'`, `sobrenome` vira `''`, `cpf`, `data_nascimento`, `observacoes` viram NULL. Telefones, e-mails e redes sociais vinculados são deletados em cascade. `anonimizado=TRUE`. Demandas vinculadas permanecem com FK preservada.

---

## 4.1. Tabela: `pessoas_telefone`

Números de telefone de uma pessoa. Tipo distingue celular de fixo. Ver ADR 0035.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | BIGSERIAL | PRIMARY KEY | |
| 🔗 `pessoa_id` * | BIGINT | FK → pessoas(id), ON DELETE CASCADE | |
| `numero` * | VARCHAR(20) | NOT NULL | Armazenado só com dígitos. Celular: 11; fixo: 10 |
| `tipo` * | VARCHAR(10) | NOT NULL | CHECK IN ('celular','fixo') |
| `eh_whatsapp` * | BOOLEAN | NOT NULL, DEFAULT FALSE | Só pode ser TRUE quando `tipo='celular'` |
| `rotulo` | VARCHAR(50) | NULL | Texto livre. Ex: "trabalho", "recado da mãe" |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Validações** (`clean()`):
- `tipo='celular'` → 11 dígitos com `9` na primeira posição após DDD (regra Anatel para móveis).
- `tipo='fixo'` → 10 dígitos.
- `eh_whatsapp=TRUE` exige `tipo='celular'`.

**Índices:** `numero`, `pessoa_id`.

**Ordenação default:** WhatsApp primeiro, depois por ordem de cadastro.

---

## 4.2. Tabela: `pessoas_email`

E-mails de uma pessoa. Pessoa pode ter múltiplos. Ver ADR 0037.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | BIGSERIAL | PRIMARY KEY | |
| 🔗 `pessoa_id` * | BIGINT | FK → pessoas(id), ON DELETE CASCADE | |
| `endereco` * | VARCHAR(254) | NOT NULL | Validação Django EmailField. Normalizado lowercase no save. |
| `rotulo` | VARCHAR(50) | NULL | Texto livre. Ex: "trabalho", "pessoal" |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Índices:** `endereco`, `pessoa_id`.

---

## 4.3. Tabela: `pessoas_redesocial`

Presença em rede social. Pessoa pode ter várias. Ver ADR 0037.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | BIGSERIAL | PRIMARY KEY | |
| 🔗 `pessoa_id` * | BIGINT | FK → pessoas(id), ON DELETE CASCADE | |
| `plataforma` * | VARCHAR(20) | NOT NULL | CHECK IN ('instagram','facebook','linkedin','x_twitter','outro') |
| `valor` * | VARCHAR(255) | NOT NULL | @handle ou URL. `@` removido no save. |
| `rotulo` | VARCHAR(50) | NULL | Texto livre. **Obrigatório** quando `plataforma='outro'`. |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Validações** (`clean()`):
- Quando `plataforma='outro'`, `rotulo` deve ser preenchido (qual rede é).

**Índices:** `plataforma`, `pessoa_id`, `valor`.

---

## 5. Tabela: `entidades`

Pessoas jurídicas, coletivos e agrupamentos de qualquer natureza. Endereço inline.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| `nome` * | VARCHAR(200) | NOT NULL | |
| `nome_fantasia` | VARCHAR(200) | NULL | |
| `tipo` * | VARCHAR(30) | NOT NULL | CHECK IN (...) — ver abaixo |
| 🔒 `cnpj` | VARCHAR(18) | UNIQUE NULLS DISTINCT | NULL para grupos informais |
| `email` | VARCHAR(254) | NULL | |
| `telefone` | VARCHAR(20) | NULL | |
| `site` | VARCHAR(255) | NULL | |
| `cep` | VARCHAR(9) | NULL | |
| `logradouro` | VARCHAR(200) | NULL | |
| `numero` | VARCHAR(20) | NULL | |
| `complemento` | VARCHAR(100) | NULL | |
| `bairro` | VARCHAR(100) | NULL | |
| `cidade` | VARCHAR(100) | NULL | |
| `estado` | VARCHAR(2) | NULL | |
| `observacoes` | TEXT | NULL | |
| `ativo` * | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| 🔗 `criado_por_id` * | UUID | FK → usuarios(id) | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| `atualizado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Valores de `tipo`:**
```
associacao_de_moradores | sindicato | partido | escola | conselho | igreja
ong | empresa | orgao_publico | coletivo | familia | grupo_informal
condominio | outros
```

`familia` e `grupo_informal` acomodam agrupamentos sem CNPJ nem endereço formal. Campos `cnpj`, `site` e endereço são todos opcionais — a tabela comporta desde uma CNPJ formal até "Família Silva" (apenas nome e tipo).

**Índices:** `nome`, `cnpj`, `tipo`, `ativo`.

---

## 6. Tabela: `vinculos`

Relação Pessoa ↔ Entidade com papel.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| 🔗 `pessoa_id` * | UUID | FK → pessoas(id), ON DELETE CASCADE | |
| 🔗 `entidade_id` * | UUID | FK → entidades(id), ON DELETE CASCADE | |
| `papel` * | VARCHAR(100) | NOT NULL | Texto livre |
| `data_inicio` | DATE | NULL | |
| `data_fim` | DATE | NULL | NULL = vínculo ativo |
| `observacao` | TEXT | NULL | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Constraint:** `data_fim >= data_inicio` quando ambos preenchidos.

**Índices:** `pessoa_id`, `entidade_id`.

---

## 7. Tabela: `tags`

Tabela única, compartilhada por pessoas, entidades e demandas.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| 🔒 `nome` * | VARCHAR(50) | NOT NULL, UNIQUE | Case-insensitive |
| `cor` | VARCHAR(7) | NULL | Hex `#RRGGBB` |
| `descricao` | TEXT | NULL | |
| `ativo` * | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Tabelas associativas M:N (criadas pelo Django automaticamente):**
- `pessoas_tags`
- `entidades_tags`
- `demandas_tags`

**Índices:** `nome` UNIQUE, `ativo`.

---

## 8. Tabela: `demandas`

Coração operacional.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| 🔒 `numero` * | VARCHAR(20) | NOT NULL, UNIQUE | Formato `D-AAMM-NNNNN` (ver ADR 0056) |
| `titulo` * | VARCHAR(200) | NOT NULL | |
| `descricao` * | TEXT | NOT NULL | |
| `origem` * | VARCHAR(15) | NOT NULL | CHECK IN ('responsiva','proativa') |
| `canal_entrada` * | VARCHAR(30) | NOT NULL | CHECK IN ('dm_instagram','whatsapp','presencial','telefone','email','oficio','indicacao_interna','redes_sociais','outro') |
| `anonimo` * | BOOLEAN | NOT NULL, DEFAULT FALSE | Demanda sem partes identificadas |
| `status` * | VARCHAR(25) | NOT NULL, DEFAULT 'novo' | CHECK IN ('novo','em_andamento','aguardando_terceiros','aguardando_pessoa','concluida','arquivado') |
| `resultado` * | VARCHAR(25) | NOT NULL, DEFAULT 'pendente' | CHECK IN ('pendente','atendido','atendido_parcialmente','nao_atendido','inviavel','nao_se_aplica') |
| `resultado_observacao` | TEXT | NULL | Anotação interna sobre o desfecho material |
| `prioridade` * | VARCHAR(10) | NOT NULL, DEFAULT 'normal' | CHECK IN ('baixa','normal','alta','urgente') |
| 🔗 `responsavel_id` | UUID | FK → usuarios(id), NULL | |
| `coordenacao_responsavel` * | VARCHAR(15) | NOT NULL | CHECK IN ('gabinete','juridico','comunicacao') |
| `restrito` * | BOOLEAN | NOT NULL, DEFAULT FALSE | TRUE = visível só p/ responsável + chefia + admin |
| `prazo` | DATE | NULL | |
| `observacoes_arquivamento` | TEXT | NULL | |
| 🔗 `criado_por_id` * | UUID | FK → usuarios(id) | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| `atualizado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| `arquivado_em` | TIMESTAMP | NULL | |

**Partes da demanda:** vinculadas via `demanda_pessoas` e `demanda_entidades` (seções 9 e 10). Não há FK direta na tabela `demandas`.

**Constraint de aplicação (validada no formulário/view):**

Demanda não-anônima precisa ter pelo menos uma parte vinculada (em `demanda_pessoas` ou `demanda_entidades`). Como a relação é M:N, a validação não pode ser CHECK de banco — é regra de negócio aplicada antes de persistir o estado final.

```python
def _validar_partes(self):
    if not self.anonimo:
        tem_pessoas = self.demanda_pessoas.exists()
        tem_entidades = self.demanda_entidades.exists()
        if not tem_pessoas and not tem_entidades:
            raise ValidationError(
                "Demanda não-anônima exige pelo menos uma parte vinculada (pessoa ou entidade)."
            )
```

**Regra de fechamento (ADR 0043):**
```python
if self.status == 'concluida':
    if self.resultado == 'pendente':
        raise ValidationError(
            "Status 'concluida' exige resultado classificado (não pode ser 'pendente')."
        )
    if self.origem == 'responsiva':
        tem_devolutiva = self.pk and self.interacoes.filter(
            tipo='devolutiva', status='realizada'
        ).exists()
        if not tem_devolutiva:
            raise ValidationError(
                "Demanda responsiva só conclui com Interação de devolutiva registrada."
            )
```

A **devolutiva ao demandante** é registrada como `Interacao(tipo='devolutiva')` na timeline — não é mais atributo da Demanda. Para demanda **proativa** (moção, indicação) o `clean()` dispensa devolutiva; basta resultado classificado.

**Arquivamento sem ter concluído exige justificativa** (em `observacoes_arquivamento`).

**Status × Resultado — duas dimensões independentes.** Detalhes da relação entre os dois em `fluxos-de-estado.md`.

**Geração de número:** método de classe `Demanda.gerar_numero()`. Formato `D-AAMM-NNNNN` (ADR 0056): prefixo `D-`, ano em 2 dígitos + mês em 2 dígitos (`AAMM` para ordenação cronológica como string), e 5 dígitos aleatórios no intervalo `10000–99999`. Colisão tratada por retry sob savepoint (max 10 tentativas) — mesmo padrão da [ADR 0051](decisoes.md#adr-0051--robustez-do-slug_publico-toctou).

**Mudanças de estado geram interações automáticas:**
- `signal post_save` em Demanda compara estado anterior vs atual.
- Ao detectar mudança em `status`, `responsavel_id` ou criação, gera Interação correspondente automaticamente.
- Detalhes em `fluxos-de-estado.md`.

**Índices:**
- `numero` (UNIQUE)
- `responsavel_id`
- `status`, `resultado`
- `(status, coordenacao_responsavel)` composto
- `(responsavel_id, status)` composto (para consulta de carga por assessor)
- `(resultado, criado_em)` composto (para análise temporal de efetividade)
- `criado_em`, `prazo`
- GIN em `to_tsvector('portuguese', titulo || ' ' || descricao)`

---

## 9. Tabela: `demanda_pessoas`

M:N entre Demanda e Pessoa, com papel.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| 🔗 `demanda_id` * | UUID | FK → demandas(id), ON DELETE CASCADE | |
| 🔗 `pessoa_id` * | UUID | FK → pessoas(id), ON DELETE RESTRICT | |
| `papel` | VARCHAR(100) | NULL | "solicitante", "afetado", "representante" — texto livre |
| `observacao` | TEXT | NULL | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Constraint UNIQUE:** `(demanda_id, pessoa_id)` — mesma pessoa não aparece duas vezes na mesma demanda.

**`ON DELETE RESTRICT` em `pessoa_id`:** impede excluir pessoa que ainda é parte de demanda ativa. Soft delete via `ativo=FALSE` é o caminho normal.

**Índices:** `demanda_id`, `pessoa_id`.

---

## 10. Tabela: `demanda_entidades`

M:N entre Demanda e Entidade, com papel.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| 🔗 `demanda_id` * | UUID | FK → demandas(id), ON DELETE CASCADE | |
| 🔗 `entidade_id` * | UUID | FK → entidades(id), ON DELETE RESTRICT | |
| `papel` | VARCHAR(100) | NULL | "representada", "parceira", "solicitante" — texto livre |
| `observacao` | TEXT | NULL | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Constraint UNIQUE:** `(demanda_id, entidade_id)`.

**Índices:** `demanda_id`, `entidade_id`.

---

## 11. Tabela: `interacoes`

Coração da rastreabilidade. Existe em três tempos: passado (`realizada`), presente e futuro (`agendada`).

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| 🔗 `demanda_id` * | UUID | FK → demandas(id), ON DELETE CASCADE | |
| 🔗 `autor_id` * | UUID | FK → usuarios(id) | |
| `tipo` * | VARCHAR(40) | NOT NULL | CHECK IN ('registro_inicial','contato_com_pessoa','contato_interno','reuniao','encaminhamento_externo','retorno_externo_recebido','devolutiva','mudanca_status','mudanca_responsavel','mudanca_resultado','arquivamento','anotacao_interna') |
| `conteudo` * | TEXT | NOT NULL | |
| `status` * | VARCHAR(15) | NOT NULL, DEFAULT 'realizada' | CHECK IN ('realizada','agendada','cancelada') |
| `data_ocorrencia` * | TIMESTAMP | NOT NULL | Data passada (realizada) ou futura (agendada) |
| `automatica` * | BOOLEAN | NOT NULL, DEFAULT FALSE | TRUE = gerada por mudança de estado da demanda |
| 🔗 `interacao_origem_id` | UUID | FK → interacoes(id), NULL | Para follow-ups: a interação que originou esta |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| `atualizado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Status:**
- `realizada` — aconteceu no passado, registrada para histórico.
- `agendada` — está marcada para acontecer no futuro. `data_ocorrencia` no futuro. Aparece em "Minhas Interações Pendentes".
- `cancelada` — foi agendada mas não vai mais acontecer. Mantida para histórico.

**Tipos:**
- **Manuais:** `registro_inicial`, `contato_com_pessoa`, `contato_interno`, `reuniao`, `encaminhamento_externo`, `retorno_externo_recebido`, `devolutiva`, `anotacao_interna`. Gerados pelos assessores. A `devolutiva` é criada exclusivamente pelo fluxo de conclusão da demanda (não aparece no seletor genérico de "adicionar interação") — registra o ato do mandato comunicando o demandante.
- **Automáticas:** `mudanca_status`, `mudanca_responsavel`, `mudanca_resultado`, `arquivamento`. Geradas por signal quando a Demanda muda. `automatica=TRUE`.

**Reunião como interação:** quando uma reunião é agendada com pessoa/entidade vinculada a demanda, é criada como interação tipo `reuniao` com status `agendada` e `data_ocorrencia` futura. Aparece tanto na timeline da demanda quanto em "Minhas próximas reuniões".

**Follow-up via `interacao_origem_id`:** quando o usuário, ao salvar uma interação, opta por criar follow-up, a nova interação criada referencia a anterior via `interacao_origem_id`. Permite reconstituir cadeias de follow-up.

**Índices:**
- `demanda_id`, `(demanda_id, data_ocorrencia DESC)` para timeline
- `(autor_id, status, data_ocorrencia)` para "Minhas pendentes"
- `(status, data_ocorrencia)` para vencidas

---

## 12. Tabela: `encaminhamentos`

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| 🔗 `demanda_id` * | UUID | FK → demandas(id), ON DELETE CASCADE | |
| `destinatario_orgao` * | VARCHAR(200) | NOT NULL | Texto livre, com autocomplete |
| `destinatario_pessoa` | VARCHAR(200) | NULL | |
| `tipo_documento` * | VARCHAR(40) | NOT NULL | CHECK IN ('oficio','requerimento_informacao','indicacao','ligacao','email','presencial','outro') |
| `numero_documento` | VARCHAR(50) | NULL | Protocolo do destinatário |
| `data_envio` * | DATE | NOT NULL | |
| `prazo_resposta` | DATE | NULL | |
| `data_resposta` | DATE | NULL | |
| `conteudo_resposta` | TEXT | NULL | |
| `status` * | VARCHAR(30) | NOT NULL, DEFAULT 'enviado' | CHECK IN ('enviado','prazo_vencido','respondido_satisfatorio','respondido_insatisfatorio','sem_resposta') |
| 🔗 `criado_por_id` * | UUID | FK → usuarios(id) | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Índices:** `demanda_id`, `destinatario_orgao`, `(prazo_resposta, status)`.

---

## 13. Tabela: `anexos`

Armazenamento de arquivos vinculados a qualquer entidade do sistema.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| 🔗 `content_type_id` * | INTEGER | FK → django_content_type(id) | Qual model está vinculado |
| `object_id` * | UUID | NOT NULL | UUID do registro vinculado |
| `arquivo` * | VARCHAR(255) | NOT NULL | Path no storage |
| `nome_original` * | VARCHAR(255) | NOT NULL | |
| `tamanho_bytes` * | BIGINT | NOT NULL | |
| `mime_type` * | VARCHAR(100) | NOT NULL | |
| `descricao` | TEXT | NULL | |
| 🔗 `enviado_por_id` * | UUID | FK → usuarios(id) | |
| `enviado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Storage local:** `media/anexos/{ano}/{mes}/{uuid}{ext}`.

**Validações:** `tamanho_bytes` ≤ 25MB; `mime_type` em whitelist.

**Entidades que aceitam anexos (MVP):** `Demanda`, `Pessoa`, `Entidade`, `Encaminhamento`.

**Implementação Django:** `GenericForeignKey('content_type', 'object_id')` via `django.contrib.contenttypes`. Não há FK de banco real para `object_id` — integridade garantida por signal `pre_delete` nos modelos vinculados, que exclui anexos órfãos antes de deletar o registro pai.

**Índice:** `(content_type_id, object_id)` composto — lookup polimórfico por objeto.

---

## 14. Tabela: `itens_inbox`

Captura rápida GTD.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| `conteudo` * | TEXT | NOT NULL | Texto bruto capturado |
| 🔗 `autor_id` * | UUID | FK → usuarios(id) | |
| `status` * | VARCHAR(15) | NOT NULL, DEFAULT 'pendente' | CHECK IN ('pendente','processado','descartado') |
| 🔗 `demanda_gerada_id` | UUID | FK → demandas(id), NULL | |
| `motivo_descarte` | TEXT | NULL | |
| `processado_em` | TIMESTAMP | NULL | |
| 🔗 `processado_por_id` | UUID | FK → usuarios(id), NULL | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Índices:** `(status, criado_em)`, `autor_id`.

---

## 15. Tabela: `solicitacoes_lgpd`

Pedidos de pessoas sobre seus dados.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| 🔑 `id` | UUID | PRIMARY KEY | |
| `tipo` * | VARCHAR(20) | NOT NULL | CHECK IN ('acesso','correcao','exclusao','portabilidade','revogacao_consentimento') |
| `nome_solicitante` * | VARCHAR(200) | NOT NULL | |
| `cpf_solicitante` | VARCHAR(14) | NULL | |
| `email_solicitante` * | VARCHAR(254) | NOT NULL | |
| `telefone_solicitante` | VARCHAR(20) | NULL | |
| `descricao` * | TEXT | NOT NULL | |
| `status` * | VARCHAR(15) | NOT NULL, DEFAULT 'pendente' | CHECK IN ('pendente','em_analise','atendido','negado') |
| 🔗 `tratado_por_id` | UUID | FK → usuarios(id), NULL | |
| `data_resposta` | DATE | NULL | |
| `conteudo_resposta` | TEXT | NULL | |
| `ip_solicitacao` | INET | NULL | |
| `criado_em` * | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 16. Auditoria (gerenciada)

Implementada com `django-auditlog`. Configuração ativa nos modelos `Pessoa`, `Entidade`, `Vinculo`, `Demanda`, `Encaminhamento`, `Anexo`, `Usuario`, `SolicitacaoLGPD`.

**Não em `Interacao` nem `ItemInbox`:** interações já são append-only por design (não se editam, apenas se cancelam); itens de inbox são efêmeros (processados ou descartados).

A biblioteca cria a tabela `auditlog_logentry` com: ação, objeto, usuário, mudanças (JSON diff), IP, timestamp. Append-only.

---

## 17. Resumo de relações

| Origem | Cardinalidade | Destino | Comentário |
|---|---|---|---|
| Usuario | N : M | Group | Perfis (Django padrão) |
| Pessoa | N : M | Entidade | Via `vinculos` |
| Pessoa | N : M | Tag | Via `pessoas_tags` |
| Pessoa | N : M | Demanda | Via `demanda_pessoas` |
| Entidade | N : M | Tag | Via `entidades_tags` |
| Entidade | N : M | Demanda | Via `demanda_entidades` |
| Demanda | 1 : N | Interacao | Manuais e automáticas |
| Demanda | 1 : N | Encaminhamento | |
| Demanda | N : M | Tag | Via `demandas_tags`. Critério de "tag-tema" definido na Fase 3 (ADR 0039). |
| Interacao | 1 : N | Interacao (auto) | Follow-up via `interacao_origem_id` |
| ItemInbox | 1 : 1 | Demanda | Quando processado |
| Anexo | N : 1 | *qualquer* | Via GenericForeignKey (Demanda, Pessoa, Entidade, Encaminhamento) |

---

*Atualizado a cada migração estrutural. Versão atual: planejamento, pré-Fase 1.*
