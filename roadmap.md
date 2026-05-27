# MPD — Mandato Parlamentar Digital

**Roadmap de Desenvolvimento**

---

## 1. Visão Geral

### 1.1. O que é o MPD

Sistema de **rastreabilidade de relacionamento político** para mandato parlamentar municipal. Núcleo: pessoa; satélites: demandas, interações, encaminhamentos. Promessa central: nenhuma demanda se perde, toda pessoa recebe retorno, e a base se enriquece com o uso.

A categoria equivalente em mandatos parlamentares anglófonos é *constituent management*. Sistema mais maduro de referência: CiviCRM (open source, AGPL v3).

### 1.2. Princípios

1. **Pessoa como núcleo**, demandas como satélites.
2. **Rastreabilidade total**: nenhum contato se perde, nenhuma demanda fica sem retorno documentado.
3. **Disciplina de fechamento**: demanda só vai para "respondida" com retorno preenchido E resultado classificado.
4. **Anti-perda estrutural**: interações podem existir no futuro (`agendada`); follow-ups são sugeridos no encerramento; mudanças geram registros automáticos.
5. **GTD**: capture primeiro (sem estrutura), estruture depois.
6. **Dados separados do código**: configuração via `.env`, sempre.
7. **Local-first, web-ready**: roda gratuitamente local, pronto para deploy.
8. **Simplicidade vence**: cada arquivo, tabela e tela existe porque resolve um problema concreto agora.
9. **Sistema é gestão da equipe também**: carga por assessor é uso de primeira classe, não derivado.

### 1.3. Stack

| Camada | Escolha |
|---|---|
| Backend | Python 3.12+ / Django 5.x |
| Banco | PostgreSQL 16+ |
| Frontend | HTMX + Alpine.js + Tailwind |
| Templates | Django Templates |
| Auditoria | django-auditlog |
| Testes | pytest + pytest-django + factory_boy |
| Lint/format | ruff + black |
| Deps | uv |

Tudo open source, gratuito enquanto local, pronto para deploy. Detalhes e justificativas em `docs/decisoes.md`.

### 1.4. Versões

- `v0.1` — Fase 0: Fundação
- `v0.2` — Fase 1: Autenticação e Usuários
- `v0.3` — Fase 2: Pessoas e Entidades
- `v0.4` — Fase 3: Casos e Interações (incluindo follow-up e interações automáticas)
- `v0.5` — Fase 4: Visões Transversais (lente de leitura sobre as partículas)
- `v0.6` — Fase 5: Inbox GTD + Minhas Pendências
- `v0.7` — Fase 6: Segurança, Visualização, Exportação (LGPD adiada — ADR 0047)
- `v0.7.1` — UX polishings nos forms de demanda
- `v0.7.2` — Fechamento de Fase 6 (segurança/auditoria/robustez — ADRs 0048–0052)
- `v0.7.3` — Cobertura de teste das Fases 4–6; exports visíveis em /auditoria (ADR 0053)
- `v1.0` — Fase 7: Polimento e Web
- `v1.1` — Fase 8: Privacidade, LGPD e lançamento público

Cada versão é tag Git, marco testável e utilizável. Não se avança sem critérios de aceite satisfeitos.

### 1.5. Documentos do projeto executivo

| Documento | Função |
|---|---|
| `roadmap.md` (este) | Cronograma faseado, critérios de pronto, validação |
| `docs/modelo-de-dados.md` | Tabelas, campos, relações, constraints |
| `docs/mapa-de-telas.md` | Rotas, perfis, ações |
| `docs/permissoes.md` | Matriz de permissões consolidada |
| `docs/fluxos-de-estado.md` | Transições de estado (Caso, Interação, ItemInbox, Encaminhamento) |
| `docs/decisoes.md` | ADRs em ordem cronológica |
| `docs/estrutura-do-repositorio.md` | Organização física do projeto |

**Regra:** o código nunca vai além do que esses documentos definem. Se durante o desenvolvimento surgir necessidade não documentada, o documento é atualizado **antes** do código.

---

## 2. Convenções

Detalhes em `docs/estrutura-do-repositorio.md`. Resumo:

- 4 apps no root (`core`, `accounts`, `pessoas`, `demandas`), sem wrapper `apps/`. (Renomeados de `cidadaos`/`casos` no início da Fase 2 — ver ADR 0018.)
- Código em inglês, produto em português.
- `models.py`, `views.py`, `tests.py` únicos por app no início.
- Sem `services/`, `permissions.py`, `signals.py` separados desde o início.
- Commits no padrão Conventional Commits.
- Branches: `main` (estável, com tags), `dev` (ativa), `feature/<nome>`.

---

## 3. Modelo de Dados (resumo)

Detalhes em `docs/modelo-de-dados.md`. Treze tabelas principais:

```
usuarios (Django auth + extensões)
pessoas ── tags (M:N) ── entidades
   │                         │
   └── vinculos ─────────────┘
   │                         │
   └── demanda_pessoas ───────┴── demanda_entidades
                  │
             demandas ──┬── interacoes (status: realizada/agendada/cancelada)
                        ├── encaminhamentos
                        └── tags (M:N)
anexos (polimórficos — vinculados a demanda, pessoa, entidade ou encaminhamento)
itens_inbox ── (FK opcional para demandas)
solicitacoes_lgpd
```

Auditoria via `django-auditlog` (sem modelagem manual). Mudanças na Demanda geram interações automáticas via signal.

---

## 4. Fases

---

### Fase 0 — Fundação

**Versão:** `v0.1`
**Objetivo:** projeto Django rodando localmente, com PostgreSQL, Tailwind compilando, página inicial servida.

#### 4.0.1. Pré-requisitos

Python 3.12+, PostgreSQL 16+, Git, conta GitHub para repositório privado.

#### 4.0.2. Especificações

1. Estrutura de diretórios conforme `docs/estrutura-do-repositorio.md`.
2. `uv` como gerenciador de dependências.
3. Settings split: `base.py`, `development.py`, `production.py`, `test.py`. Default: development.
4. `.env` via `django-environ`. `.env.example` versionado, `.env` no `.gitignore`.
5. PostgreSQL local com banco `mpd_dev`.
6. Tailwind via `django-tailwind` ou CLI standalone.
7. HTMX e Alpine via CDN no MVP.
8. Pre-commit: `ruff`, `black`, `detect-secrets`.
9. pytest configurado.
10. README.md completo.
11. Página inicial `/` com nome do mandato (de `.env`).
12. Repositório no GitHub privado, primeiro commit.

#### 4.0.3. Critérios de Aceite

- [x] `python manage.py runserver` inicia sem erros.
- [x] `http://localhost:8000/` retorna página estilizada.
- [x] `python manage.py migrate` sem erros.
- [x] `python manage.py createsuperuser` funciona.
- [x] `pytest` passa.
- [x] `ruff check .` e `black --check .` passam.
- [x] README permite clonar e rodar do zero.
- [x] Tag `v0.1` no GitHub.

#### 4.0.4. Validação

```bash
pytest -v
ruff check .
black --check .
python manage.py check
python manage.py makemigrations --check --dry-run
```

#### 4.0.5. Verificação Manual (Pedro)

1. Clonar repositório em outra pasta.
2. Seguir literalmente o README.
3. Ver página inicial no navegador.
4. Logar no `/admin/`.

---

### Fase 1 — Autenticação e Usuários

**Versão:** `v0.2`
**Objetivo:** autenticação funcional e infraestrutura de usuários. Grupos e permissões entram nas fases em que os models que eles protegem são criados.

#### 4.1.1. Pré-requisitos

Fase 0 concluída.

#### 4.1.2. Especificações

1. App `accounts`. Modelo `Usuario` herdando de `AbstractUser`. Campos extras: `nome_completo`, `cargo`. Email é único e usado para login. Flag `is_staff` distingue quem pode gerenciar outros usuários.
2. Login/logout com templates Tailwind.
3. Política de senha: mínimo 8 caracteres, sem exigências de complexidade (maiúsculas, números, caracteres especiais). Senhas obviamente comuns bloqueadas (ex: "password", "12345678").
4. Sessão: 12h de inatividade; "lembrar-me" estende para 30 dias.
5. Comando `criar_usuarios_iniciais` cria um usuário `is_staff` e um usuário comum para facilitar o setup local.
6. Fixture com dados fictícios.
7. Página de perfil pessoal.
8. Gerenciamento de usuários (apenas `is_staff=True`).

#### 4.1.3. Critérios de Aceite

- [x] URL não pública redireciona para login.
- [x] Usuário consegue logar e fazer logout.
- [x] Usuário `is_staff` consegue criar/editar/desativar outros usuários.
- [x] Usuário sem `is_staff` recebe 403 ao tentar gerenciar usuários.
- [x] Senhas fracas rejeitadas.
- [x] `criar_usuarios_iniciais` funciona.
- [x] Logout invalida sessão.

#### 4.1.4. Validação

```bash
pytest accounts/ -v --cov=accounts
ruff check .
python manage.py check
```

#### 4.1.5. Verificação Manual

1. Rodar `criar_usuarios_iniciais`.
2. Logar com o usuário `is_staff`, criar um novo usuário, logar com o novo usuário.
3. Tentar acessar `/configuracoes/usuarios` com usuário comum → 403.
4. Logout e confirmar redirect.

---

### Fase 2 — Pessoas e Entidades

**Versão:** `v0.3`
**Objetivo:** núcleo de relacionamento funcional. Cadastrar, buscar, vincular, classificar com tags.

#### 4.2.1. Pré-requisitos

Fase 1 concluída.

#### 4.2.2. Especificações

0. **Renomear apps:** `cidadaos/` → `pessoas/`, `casos/` → `demandas/` (antes de criar qualquer model). Atualizar `INSTALLED_APPS`.
1. App `pessoas` com modelos: `Pessoa`, `Telefone`, `EmailPessoa`, `RedeSocial`, `Entidade`, `Vinculo`, `Tag`.
2. **Endereço inline** em `Pessoa` e `Entidade`.
3. **Contatos como entidades plurais** agrupados na seção "Contatos" do form (ADR 0037):
   - **Telefones** (M:1): tipo (`celular`/`fixo`), `eh_whatsapp`, rótulo opcional (ADR 0035).
   - **E-mails** (M:1): endereço + rótulo opcional.
   - **Redes sociais** (M:1): plataforma (`instagram`/`facebook`/`linkedin`/`x_twitter`/`outro`) + valor + rótulo (obrigatório se `outro`).
4. Validações: pelo menos 1 canal (qualquer dos 3); bairro/cidade obrigatórios; CPF válido por algoritmo; celular com 11 dígitos começando com 9 após DDD; fixo com 10 dígitos.
5. **Integração ViaCEP**: módulo `pessoas/viacep.py`. Tolerante a falha.
6. **Deduplicação**: CPF UNIQUE NULLS DISTINCT; alerta AJAX por similaridade em email, telefone ou rede social.
7. Tags livres (sem categoria) — etiquetas dinâmicas para agrupar pessoas/entidades/demandas. Ver ADR 0039.
8. Telas conforme `docs/mapa-de-telas.md` (seções 6 e 7).
9. **Criar grupos padrão** (Administrador, Chefe de Gabinete, Coordenador, Assessor) via data migration com as permissões dos models desta fase. Permissões de `demandas` adicionadas na Fase 3. Matriz completa em `docs/permissoes.md`.
10. Soft delete via campo `ativo`.
11. Django Admin com fieldsets organizados.

#### 4.2.3. Critérios de Aceite

- [x] Renomear apps concluído; migrate sem erros.
- [x] Cadastrar pessoa completa, sem demanda, funciona.
- [x] Cadastro sem nenhum canal (telefone, email, rede social) rejeitado com mensagem clara.
- [x] Pessoa aceita múltiplos telefones; celular com 9 e 11 dígitos válido; fixo com 10 dígitos válido.
- [x] Pessoa aceita múltiplos e-mails e múltiplas redes sociais.
- [x] Rede social com plataforma="Outro" exige rótulo.
- [ ] CEP válido auto-preenche endereço.
- [x] CPF duplicado bloqueado.
- [ ] Email/telefone duplicado mostra alerta amarelo, mas permite criar.
- [x] Lista pagina, busca, filtra.
- [x] Cadastrar entidade (inclusive tipo `familia` ou `grupo_informal`) e vincular pessoa funciona.
- [x] Tag criada e atribuída.
- [x] Permissões respeitadas por perfil.
- [x] Soft delete remove de listagem mas preserva no banco.

#### 4.2.4. Validação

```bash
pytest pessoas/ -v --cov=pessoas
```

#### 4.2.5. Verificação Manual

1. Cadastrar 5 pessoas com variações.
2. Tentar duplicado e ver alerta.
3. Cadastrar "Família Silva" como Entidade tipo `familia` e vincular 3 pessoas.
4. Cadastrar associação fictícia com CNPJ e vincular pessoas.
5. Criar tags e atribuir.
6. Buscar por nome, bairro, tag.
7. Logar como diferentes perfis e verificar permissões.
8. Desativar pessoa.

---

### Fase 3 — Demandas e Interações

**Versão:** `v0.4`
**Objetivo:** coração operacional. Demandas com múltiplas partes (M:N), timeline de interações (manuais e automáticas), encaminhamentos, anexos polimórficos, regra inviolável de fechamento, schedule follow-up.

#### 4.3.1. Pré-requisitos

Fase 2 concluída.

#### 4.3.2. Especificações

1. App `demandas` com modelos: `Demanda`, `DemandaPessoa`, `DemandaEntidade`, `Interacao`, `Encaminhamento`, `Anexo`, `ItemInbox`.
2. **Regra de fechamento** codificada conforme `docs/fluxos-de-estado.md`: status `respondido` exige `retorno_data`, `retorno_conteudo` E `resultado` ≠ `pendente`.
3. **Partes M:N**: formulário de criação exige ao menos uma parte (pessoa ou entidade) vinculada, ou flag `anonimo=True`. Validado no formulário/view.
4. **Geração de número** com retry em colisão. Formato `D-AAMM-NNNNN` (ver ADR 0056 — supersede o `MPD-AAAA-NNNNN` original).
5. **Tema da demanda** = uma tag vinculada via M:N. Critério de "qual tag pode ser tema" decidido na ADR de implementação (ver ADR 0039).
6. **Visibilidade** via boolean `restrito`.
7. **Resultado da demanda**: campo `resultado` com 6 valores + campo `resultado_observacao`. Editável a qualquer momento por quem pode editar a demanda.
8. **Interação com status `agendada`/`realizada`/`cancelada`**.
9. **Schedule Follow-up**: ao salvar interação como `realizada`, formulário oferece criar follow-up.
10. **Interações automáticas via signal** em mudanças da Demanda. Marcadas com `automatica=TRUE`.
11. **Janela de edição de 24h** para interações `realizada` pelo autor.
12. **Reunião como Interação** tipo `reuniao` com data futura — não há módulo Agenda separado.
13. **Anexos polimórficos**: via `GenericForeignKey` — upload disponível no detalhe de Demanda, Pessoa, Entidade e Encaminhamento. Validação de tamanho (≤25MB) e mime type.
14. Telas conforme `docs/mapa-de-telas.md` (seções 8, 9).
15. **Expandir permissões dos grupos** via data migration com as permissões customizadas dos models desta fase.

#### 4.3.3. Critérios de Aceite

- [x] Criar demanda vinculando múltiplas pessoas funciona.
- [x] Criar demanda anônima funciona com flag.
- [x] Criar demanda vinculada apenas a entidade funciona.
- [x] Demanda recém-criada tem `resultado='pendente'` por default.
- [x] Mudar status para "respondido" sem retorno → bloqueado.
- [x] Mudar status para "respondido" com `resultado='pendente'` → bloqueado com mensagem clara.
- [x] Atualizar `resultado` em qualquer status da demanda funciona.
- [x] Mudança de `resultado` gera interação automática `mudanca_resultado` na timeline.
- [x] Adicionar interação `realizada` registra na timeline.
- [x] Adicionar interação `agendada` (com data futura) aparece em "minhas pendências".
- [x] Schedule Follow-up: ao encerrar interação, oferta cria follow-up agendado.
- [x] Cadeia de follow-up reconstrutível via `interacao_origem_id`.
- [x] Mudar status da demanda gera interação automática na timeline.
- [x] Mudar responsável gera interação automática.
- [x] Interação `automatica=TRUE` é imutável (não editável por ninguém).
- [x] Janela de 24h: editar interação própria recém-criada funciona; após 24h, bloqueada.
- [x] Adicionar encaminhamento aparece na timeline.
- [x] Anexo pendurado na Demanda aceito; anexo pendurado no Encaminhamento aceito.
- [x] Anexo de 30MB rejeitado; de 5MB aceito.
- [x] Detalhe da pessoa lista todas as demandas vinculadas.
- [x] Filtro "Minhas demandas" funciona.
- [x] Demanda restrita não aparece para CO de outra coordenação.

#### 4.3.4. Validação

```bash
pytest demandas/ -v --cov=demandas
```

#### 4.3.5. Verificação Manual

1. Como AS, criar demanda a partir de pessoa existente + vincular uma entidade como parte. Tema "Saúde", canal "WhatsApp".
2. Adicionar segunda pessoa à demanda como "afetada".
3. Adicionar interação `realizada` simulando ligação.
4. Ao salvar, marcar "criar follow-up" e agendar próxima ligação para 7 dias.
5. Verificar que a interação agendada aparece em "Minhas Interações Pendentes".
6. Adicionar encaminhamento à Sesa. Fazer upload do ofício enviado (anexo no encaminhamento).
7. Atualizar `resultado` para `atendido_parcialmente` com observação. Verificar interação automática `mudanca_resultado` na timeline.
8. Tentar marcar demanda como respondida sem retorno → erro.
9. Tentar marcar demanda como respondida com retorno mas resultado `pendente` → erro.
10. Preencher retorno e marcar respondida (resultado já estava classificado) → sucesso.
11. Ver na timeline a interação automática "Status: em_andamento → respondido".
12. Reatribuir a demanda a outro assessor → ver interação automática "Mudança de responsável".
13. Criar demanda proativa (moção), anônima, com flag.
14. Marcar demanda proativa com `resultado='nao_se_aplica'` → permitido.
15. Como CO Jurídico, tentar demanda restrita de Comunicação → bloqueado.
16. Filtrar por "vencidas" e "sem retorno há +30 dias".
17. Detalhe da pessoa mostra todas as demandas vinculadas.
18. Editar interação 1h após criar → permitido. Após 25h → bloqueado.

---

### Fase 4 — Visões Transversais

**Versão:** `v0.5`
**Objetivo:** lente de leitura agregada sobre as partículas que orbitam a Demanda (encaminhamentos), sem criar entidades autônomas. Demanda continua sendo o núcleo conceitual e o único ponto de edição. As listas cross são deep-links de volta para a Demanda.

#### 4.4.1. Pré-requisitos

Fase 3 concluída.

#### 4.4.2. Especificações

1. **Lista de Encaminhamentos** (`/encaminhamentos/`)
   - Leitura agregada, paginada (25/pg). Cada linha é deep-link para a Demanda associada (não tem detalhe próprio de encaminhamento).
   - Colunas: tipo de documento + órgão (ex.: "Indicação → Semus"), demanda (número como link), data envio, prazo (badge vermelho se vencido), status atual.
   - Filtros: status (enviado / prazo vencido / respondido satisfatório / respondido insatisfatório / sem resposta), órgão (autocomplete dos órgãos já usados), tipo de documento.
   - Quick filters: "Aguardando resposta", "Prazo vencido", "Respondidos esta semana".
   - Respeita a visibilidade da Demanda associada — usuário sem permissão para a Demanda não vê o Encaminhamento na lista.
   - Sem botão "+ Novo" na própria lista. Encaminhamento só nasce dentro de uma Demanda.

2. **Quick filters operacionais novos nas listas existentes**
   - `/demandas/`: "Com encaminhamento aberto", "Sem encaminhamento".
   - `/pessoas/`: "Com demanda em aberto".
   - `/entidades/`: "Com demanda em aberto".

3. **Topbar** ganha link "Encaminhamentos" depois de "Entidades".

4. **Documentação**
   - ADR 0046 registra a inserção da fase e o princípio "Demanda como núcleo; partículas não viram entidades autônomas".
   - `mapa-de-telas.md` atualizado com a rota `/encaminhamentos/`.

#### 4.4.3. Critérios de Aceite

- [x] `/encaminhamentos/` lista todos os Encaminhamentos visíveis ao usuário, paginados.
- [ ] Filtros (status, órgão, tipo documento) e quick filters funcionam isoladamente e em combinação. *(cobertura parcial — só "vencidos" tem teste; combinações ficam como dívida)*
- [x] Visibilidade respeita a restrição da Demanda: encaminhamento de demanda restrita não aparece para quem não pode ver a demanda.
- [ ] Linha de encaminhamento leva ao detalhe da Demanda associada. *(verificação manual — link de template)*
- [x] `/demandas/` mostra os novos quick filters; resultados coerentes.
- [x] `/pessoas/` e `/entidades/` mostram os novos quick filters; resultados coerentes. *(v0.7.3: cobertura de `/entidades/` adicionada)*
- [ ] Topbar tem link "Encaminhamentos" para quem tem `demandas.view_encaminhamento`. *(verificação manual)*

#### 4.4.4. Validação

```bash
pytest demandas/ -v -k "encaminhamento_lista or visao_transversal"
```

#### 4.4.5. Verificação Manual

1. Como ADM, abrir `/encaminhamentos/`. Confirmar listagem.
2. Filtrar por órgão "Semus". Confirmar redução.
3. Quick filter "Prazo vencido". Confirmar lista de vencidos.
4. Clicar em uma linha → cai no detalhe da Demanda com o encaminhamento expandido.
5. Como Assessor de Comunicação, abrir `/encaminhamentos/`. Confirmar que encaminhamentos de demandas restritas de outras coordenações não aparecem.
6. Em `/demandas/`, clicar "Com encaminhamento aberto". Confirmar lista.
7. Em `/pessoas/`, clicar "Com demanda em aberto". Confirmar lista.

---

### Fase 5 — Inbox GTD e Minhas Pendências

**Versão:** `v0.6`
**Objetivo:** captura rápida em segundos, triagem em momento separado. Visão consolidada das pendências do usuário.

#### 4.4.1. Pré-requisitos

Fase 3 concluída.

#### 4.4.2. Especificações

1. **Modelo `ItemInbox`** em `demandas/models.py`.
2. **Captura rápida** — três formas:
   - Atalho `Ctrl+K` / `Cmd+K` em qualquer página.
   - Botão flutuante (FAB) sempre visível.
   - Página `/inbox/capturar`.
3. Modal de captura: foco automático, `Enter` envia, `Shift+Enter` quebra linha, `Esc` fecha. HTMX, sem reload. Confirmação visual de 1s.
4. Lista `/inbox` com filtros e indicadores visuais (laranja +7d, vermelho +30d).
5. Tela de processamento: converte item bruto em caso estruturado, ou descarta com motivo.
6. **Tela `/minhas-pendencias`**: consolida todas as Interações onde o usuário é autor com `status='agendada'`. Ordenadas por `data_ocorrencia` (vencidas no topo). Agrupadas (Hoje / Amanhã / Esta semana / Próximas).
7. **Tela `/minhas-reunioes`**: view filtrada de pendências, apenas tipo `reuniao`. Próximos 30 dias.
8. **Badge de pendências vencidas** na topbar do usuário (atualiza ao trocar de página).
9. Telas conforme `docs/mapa-de-telas.md` (seções 4, 5, 9).
10. Permissões: todos podem capturar e processar.

#### 4.4.3. Critérios de Aceite

- [ ] `Ctrl+K` em qualquer página abre modal. *(verificação manual — JS de browser)*
- [x] Texto enviado vira `ItemInbox` pendente.
- [ ] Modal fecha sem perder contexto da página anterior. *(verificação manual — JS de browser)*
- [x] Badge de pendências vencidas aparece na topbar.
- [x] Lista `/inbox` mostra pendentes com indicadores visuais. *(v0.7.3: filtros + badges amber/red testados)*
- [x] Processar gera caso e marca item processado.
- [x] Caso gerado tem conteúdo do item como descrição inicial.
- [x] Descartar pede motivo e registra.
- [x] `/minhas-pendencias` lista todas as interações agendadas do usuário.
- [x] Pendências vencidas aparecem em vermelho no topo.
- [x] Marcar pendência como realizada (a partir de "minhas pendências") funciona. *(v0.7.3: fluxo coberto)*
- [x] `/minhas-reunioes` filtra apenas tipo `reuniao`.

#### 4.4.4. Validação

```bash
pytest demandas/ -v -k "inbox or pendencia"
```

#### 4.4.5. Verificação Manual

1. Como AS, `Ctrl+K`, digitar "minutar moção de aplausos para João da Silva pelo prêmio internacional", enviar.
2. Confirmar que aparece em `/inbox`.
3. Como CO Jurídico, processar: vincular pessoa "João da Silva" (criar se não existir), tema "Homenagem", origem proativa.
4. Confirmar que demanda foi criada.
5. Capturar 3 itens em sequência rápida.
6. Descartar um com motivo.
7. Como AS, criar interação agendada para amanhã. Verificar em `/minhas-pendencias`.
8. Avançar relógio (ou criar interação com data passada). Ver pendência vencida no topo.
9. Marcar pendência como realizada via botão.
10. Criar interação tipo `reuniao` agendada. Verificar em `/minhas-reunioes`.

---

### Fase 6 — Segurança, Visualização, Exportação ✅

**Versão:** `v0.7` (escopo principal) + `v0.7.1` (UX polishings) + `v0.7.2` (fechamento via ADRs 0048–0052)
**Status:** **fechada em 2026-05-17** após revisão técnica externa que identificou e endereçou 5 gaps de segurança/robustez. Detalhes nas ADRs 0048–0052 ([`docs/decisoes.md`](./docs/decisoes.md)).
**Objetivo:** amplificar o trabalho da equipe. Filtros poderosos para encontrar; exportação para preparar relatórios; painel para ver o mandato em números; auditoria UI para rastreabilidade interna; infra básica para confiabilidade operacional.

> **Mudança de escopo (ADR 0047):** privacidade/LGPD adiada para a Fase 8 (v1.1). MVP é uso interno do mandato, sem exposição pública — urgência de compliance só aparece com hospedagem aberta.

#### 4.6.1. Pré-requisitos

Fase 5 concluída.

#### 4.6.2. Especificações

1. **Filtros avançados via querystring** em todas as listagens (Demandas, Pessoas, Entidades, Encaminhamentos, Inbox). Filtros são combináveis e preservados na paginação. Inclui filtro por intervalo de datas (`criado_em`, `data_envio`, etc.).

2. **Exportação CSV**: UTF-8 com BOM (para o Excel BR ler acentos), separador `;`. Endpoints `/demandas/export.csv`, `/pessoas/export.csv`, `/encaminhamentos/export.csv`. Permissão CO+. Limite de 10.000 registros por exportação. Toda exportação registra entrada no auditlog (quem, quando, filtros aplicados, total).

3. **Painel `/analise`** (CO+) com 5-6 contagens textuais e visuais:
   - Demandas por tema.
   - Demandas por mês (últimos 12 meses).
   - Demandas por coordenação.
   - Top 20 pessoas com mais demandas (sem incluir anônimas).
   - Encaminhamentos pendentes por órgão.
   - Carga por assessor: demandas abertas, vencidas, tempo médio até conclusão.

   Cada métrica oferece **toggle "Tabela / Gráfico"**. Gráficos via Chart.js (CDN, sem build step). Tabela é o default (lê rápido, acessível, navegável por keyboard).

4. **Auditoria UI `/auditoria`** (CG+): lista cronológica das entradas do `auditlog_logentry`, paginada (50/pg). Filtros: usuário, content type (modelo), período, ação (criar / alterar / deletar). Cada entrada com **diff visual antes-vs-depois** campo a campo. Log não-editável (já garantido pelo modelo do auditlog).

5. **Health check `/healthz`**: endpoint público que verifica conexão ao banco. Retorna `200 OK` com body `"ok"` se tudo bem, `503` caso contrário.

6. **Backup**: script `scripts/backup.sh` que executa `pg_dump` para arquivo `backup-AAAA-MM-DD-HHMMSS.sql`. Documentado no README com instruções de uso (cron diário).

7. **Verificação de integridade**: comando `manage.py verificar_integridade` que reporta:
   - Demandas responsivas em `status=concluida` sem Interação `tipo=devolutiva` realizada.
   - Anexos órfãos (arquivo em disco sem registro, ou registro sem arquivo).
   - Encaminhamentos com `prazo_resposta < hoje` e `status=enviado` (cron de atualização não rodou).
   - `ItemInbox.status=pendente` há mais de 90 dias.
   - Interações `agendada` há mais de 180 dias sem ação.

   Saída em texto, código de saída 0 se nada encontrado, 1 caso contrário (útil para cron monitorado).

#### 4.6.3. Critérios de Aceite

- [x] Filtros combinam via querystring corretamente e são preservados na paginação.
- [x] CSV abre no Excel BR com acentuação correta.
- [x] Exportação registra log no auditlog (via `core.utils.registrar_export`).
- [x] Painel `/analise` carrega em < 1s para 1000 registros.
- [x] Cada métrica do painel oferece toggle tabela/gráfico e ambos renderizam os mesmos números.
- [x] Editar uma Pessoa registra log com diff visível em `/auditoria`.
- [x] Filtros em `/auditoria` (usuário/modelo/período) funcionam.
- [x] `/healthz` retorna 200 quando o banco está acessível.
- [x] `backup.sh` gera dump válido (verificável com `pg_restore --list`).
- [x] `verificar_integridade` detecta cada um dos 5 casos da especificação. *(v0.7.3: cobertura de teste para todos os 5 ramos)*
- [x] **v0.7.2:** Painel `/analise` respeita visibilidade restrita (ADR 0049). `Interacao` e `ItemInbox` no auditlog (ADR 0050). `slug_publico` com retry (ADR 0051). Checagem de papel centralizada (ADR 0048).
- [x] **v0.7.3:** `registrar_export` grava `LogEntry` — exportações ficam visíveis em `/auditoria` (ADR 0053). Cobertura de teste fechada nos critérios remanescentes das Fases 4–6.

#### 4.6.4. Validação

```bash
uv run pytest -v
uv run python manage.py verificar_integridade
bash scripts/backup.sh /tmp/test-backup
curl http://localhost:8000/healthz
```

#### 4.6.5. Verificação Manual

1. Filtrar pessoas por bairro + tag, exportar CSV. Abrir no Excel BR — acentos OK.
2. Como Coordenador, abrir `/analise` e alternar tabela/gráfico em cada métrica.
3. Editar uma Pessoa via UI; ir em `/auditoria` e ver o registro com diff.
4. Rodar `backup.sh`, inspecionar o arquivo gerado.
5. Criar inconsistência intencional (ex.: encaminhamento com prazo passado e status enviado), rodar `verificar_integridade`, ver o relato.

---

### Fase 7 — Polimento e Web

**Versão:** `v1.0`
**Objetivo:** sistema pronto para uso interno do gabinete e deploy.

> **Insumos da revisão técnica de fim-de-Fase-6 (2026-05-17)** ficaram registrados em `docs/debito-tecnico.md` como DTs e atravessam o escopo desta fase. Itens relevantes: DT-011 (gestão de usuários via Groups), DT-013 (drop de `papel` ornamental), DT-014 (filtros combinados), DT-015–017 (higiene de testes). Cada um aparece nas especificações ou nos critérios de aceite abaixo, com a referência ao DT.

#### 4.6.1. Pré-requisitos

Fase 6 concluída (v0.7.3 — incluindo fechamento via ADRs 0048–0053).

#### 4.6.2. Especificações

1. **UX**:
   - Revisão mobile (320–768px), empty states, mensagens claras.
   - **Modal de confirmação ao classificar `resultado`** no painel "Estado" da Demanda — ação é one-way (clean() bloqueia volta a `pendente`), usuário precisa saber antes de clicar. Levantado na revisão técnica como UX subótimo com consequência permanente.
2. **Documentação**: `docs/manual.md` (manual de uso para a equipe), `docs/deploy.md`.
3. **Configuração de produção**:
   - `production.py` revisado, Whitenoise, logging estruturado, Sentry opcional.
   - **Backup robusto** (revisão técnica): trocar `scripts/backup.sh` plano para `pg_dump -Fc` (custom format — compressão + restore seletivo); rotação automática (manter 7 diários + 4 semanais); encriptação at-rest (gpg ou age) para arquivos com PII. Smoke test em CI verifica que `pg_restore --list` no dump gerado retorna ≥1 tabela.
4. **Docker**: `Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`.
5. **Performance**:
   - Auditoria de queries, `select_related`/`prefetch_related`, gzip.
   - Confirmar que `/analise` carrega em <1s para 1000 demandas (critério §4.6.3 da Fase 6 não testado em CI — validação manual com `criar_dados_teste` em escala).
6. **Acessibilidade básica**: contraste WCAG AA, navegação por teclado, `aria-label`.
7. **Compatibilidade**: Chrome, Firefox, Safari, Edge (últimas 2 versões).
8. **Permissões — fechar DT-011**:
   - Criar permissão customizada `accounts.gerenciar_usuarios`; migrar `UsuarioListView`/`CreateView`/`UpdateView`/`ToggleAtivoView` de `StaffRequiredMixin` para `PermissionRequiredMixin`.
   - Atribuir a permissão ao grupo `Administrador` via data migration.
   - Forms deixam de expor `is_staff` editável; promoção a staff/superuser fica reservada ao Django Admin.
   - Remover `StaffRequiredMixin` de `accounts/views.py`.
9. **Limpeza**:
   - Drop de `papel`/`papel_outro` em `DemandaPessoa`/`DemandaEntidade` (ADR 0054 — DT-013).
   - Atualizar dependências.
   - Remover código morto.
10. **Higiene de testes (DT-014 a DT-017)**:
    - DT-014: ≥2 testes por listagem principal cobrindo combinações de filtros (`?status=...&coord=...&tema=...`).
    - DT-015: corrigir `tipo="associacao"` para valor real do `TIPO_CHOICES`.
    - DT-016: teste de regressão para `?ate=` em `/auditoria`.
    - DT-017: trocar assert de classe Tailwind por `data-envelhecimento` em `/inbox/`.

#### 4.6.3. Critérios de Aceite

- [ ] Telas funcionam em smartphone.
- [ ] Manual revisado por um assessor leigo.
- [ ] `docker compose up` sobe ambiente de desenvolvimento.
- [ ] Documentação de deploy permite hospedar em VPS em <2h.
- [ ] Lighthouse: Performance ≥ 85, Accessibility ≥ 90.
- [ ] Sem warnings no console.
- [ ] **DT-011 fechado**: `grep -r 'is_staff' accounts/views.py accounts/forms.py` não encontra checagens de gating (apenas o campo no model). Promoção via Admin Django apenas.
- [ ] **DT-013 fechado**: campo `papel`/`papel_outro` removido de `DemandaPessoa` e `DemandaEntidade` (ADR 0054); formulário de demanda e tela de processar inbox não exibem mais o seletor.
- [ ] **DT-014 fechado**: ≥2 testes por listagem principal cobrem combinações de filtros via querystring; §4.4.3 marca filtros combinados como `[x]`.
- [ ] **DT-015–017 fechados**: 3 ajustes de higiene aplicados.
- [ ] **Backup**: `scripts/backup.sh` usa `-Fc`, gera arquivo encriptado e respeita rotação. CI roda smoke test (`pg_restore --list` >0 linhas).
- [ ] **EstadoForm**: classificar `resultado` exibe modal de confirmação no front; usuário confirma explicitamente antes da ação one-way.
- [ ] Painel `/analise` carrega em < 1s para 1000 registros (validação manual com `criar_dados_teste` em escala).
- [ ] Tag `v1.0` no GitHub com release notes.

#### 4.6.4. Validação

```bash
pytest -v --cov --cov-report=html
ruff check .
black --check .
python manage.py check --deploy
docker compose build
docker compose up -d
curl http://localhost:8000/healthz
```

#### 4.6.5. Verificação Manual

1. Usar o sistema no celular por 30 minutos.
2. Convidar 2 assessores e fazer onboarding sem assistência.
3. Refinar manual conforme dúvidas.
4. Fluxo completo: pessoa chega por WhatsApp → captura no inbox → processado → demanda → encaminhamento → retorno → resposta → arquivamento.
5. Conferir auditoria de toda a operação.

---

### Fase 8 — Privacidade, LGPD e lançamento público

**Versão:** `v1.1`
**Objetivo:** habilitar o sistema para o mundo fora da equipe interna. Conformidade LGPD completa + porta pública + ajustes de exposição. Decisão tomada na ADR 0047 (adiamento da LGPD da Fase 6, agrupada agora com o esforço natural de "abrir pro mundo").

#### 4.8.1. Pré-requisitos

Fase 7 (Polimento e Web) concluída — sistema com `v1.0` em uso interno por algumas semanas, dores reais conhecidas.

#### 4.8.2. Especificações

1. **Política de privacidade pública** (`/privacidade`): texto LGPD-compliant explicando bases legais de tratamento, dados coletados, finalidades, direitos do titular, contato do Encarregado.

2. **Encarregado (DPO) declarado**: nome + email visíveis na página de privacidade. Configurável via settings.

3. **Canal público de solicitação LGPD** (`/privacidade/solicitar`):
   - Formulário público (sem login), com rate limiting (10 submissões/min/IP).
   - Tipo de solicitação: acesso, retificação, anonimização, portabilidade.
   - Identificação do solicitante (nome, email, CPF opcional para autenticação).
   - Conteúdo livre.

4. **Modelo `SolicitacaoLGPD`** em `accounts/models.py`: armazena solicitações, com status (pendente, em_análise, atendida, negada), responsável atribuído, motivo da resposta.

5. **Lista interna `/configuracoes/lgpd`** (Encarregado / Admin):
   - Inbox de solicitações pendentes.
   - Botões: atribuir a si, gerar export dos dados, anonimizar Pessoa associada.
   - Trilha de cada solicitação no auditlog.

6. **Export dos dados de uma Pessoa**:
   - Botão "Exportar dados (LGPD)" no detalhe de Pessoa (com permissão).
   - Gera JSON estruturado + opcionalmente PDF render (decisão entre `xhtml2pdf`, `weasyprint`, etc. na época).
   - Inclui: dados cadastrais, contatos, vínculos, demandas em que a pessoa é parte (resumo, sem dados de terceiros), interações em que a pessoa aparece.

7. **Anonimização exposta na UI**:
   - Botão "Anonimizar (LGPD)" no detalhe de Pessoa, com confirmação dupla.
   - Reuso de `Pessoa.anonimizar()` (já existe).

8. **Hardening de exposição pública**:
   - Headers de segurança (HSTS, X-Frame-Options, CSP básica).
   - Robots.txt definido.
   - Páginas de erro customizadas (`404.html`, `500.html`, `403.html`).
   - Logs de auditoria de acessos suspeitos (já temos `django-axes` para login; estender para tentativas em endpoints sensíveis).

#### 4.8.3. Critérios de Aceite

- [ ] `/privacidade` acessível sem login, com texto e contato do Encarregado.
- [ ] Submissão pública de solicitação LGPD gera `SolicitacaoLGPD` pendente.
- [ ] Rate limiting bloqueia 11ª submissão em 1 minuto.
- [ ] Encarregado vê lista, processa, gera export.
- [ ] Export contém todos os dados pessoais e nada de terceiros.
- [ ] Anonimização preserva contagens históricas e remove identificadores.
- [ ] Headers de segurança presentes no HTML servido.

#### 4.8.4. Validação

```bash
uv run pytest accounts/ demandas/ -k "lgpd"
curl -I https://produção.mpd.local/  # confere headers
```

#### 4.8.5. Verificação Manual

1. Acessar `/privacidade` deslogado.
2. Submeter solicitação LGPD pública.
3. Como Encarregado, processar a solicitação, gerar export.
4. Anonimizar Pessoa de teste; demandas históricas continuam contando mas sem PII.
5. Conferir headers de segurança via `curl -I`.

---

## 5. Pós-MVP — Roadmap de Evolução

A partir de `v1.0`, evolução guiada por uso real.

### v1.x — Refinamentos
- Engagement Score por cidadão (pontuação automática a partir das interações).
- Smart Groups (filtros nomeados que se atualizam sozinhos).
- Notificações por e-mail (caso atribuído, prazo próximo, retorno recebido).
- Dashboards visuais (Chart.js).
- Importação em lote via CSV.
- Newsletter para a base (preferências de comunicação serão reintroduzidas conforme regra real do disparo — ver ADR 0034).

### v2.x — Mandato
- **Proposições legislativas** (PL, RI, indicação, moção) com vínculo N:N a casos.
- **Agenda do mandato** como módulo dedicado, com calendário visual e integração Google Calendar.
- **Multi-endereço** por cidadão.
- **Geocodificação de endereços** de Pessoa e Entidade (lat/long persistidos, signal assíncrono, Nominatim como provedor padrão e Google como fallback opcional). Habilita heatmaps territoriais e análise por bairro/região. Ver ADR 0036.
- **Multi-tenant** (ativação para virar SaaS).

### v3.x — Inteligência e Integrações
- **Motor jurídico**: geração de minutas a partir de templates (com Claude API).
- **Extração com IA**: ItemInbox texto livre vira sugestão estruturada.
- **WhatsApp Business API** (captura automática em inbox).
- **Instagram DMs**.
- **API REST pública**.
- **Convenção `[caso #N]` em e-mail** para integração simples.

### v4.x — Comercial
- Onboarding self-service de novos mandatos.
- Billing.
- Marketing site.
- App mobile nativo.

---

## 6. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Equipe não adota (continua no WhatsApp solto) | Alta | Alto | Captura rápida realmente fácil; onboarding cuidadoso; exemplos concretos |
| Performance degrada com base grande | Média | Médio | Índices bem definidos; paginação; otimização na Fase 7 |
| Vazamento de dados | Baixa | Crítico | Auditoria desde Fase 6; hospedagem BR; backup criptografado |
| Demanda LGPD inesperada | Média | Alto | Política definida na Fase 6; controlador identificado |
| Pedro fica dependente de Claude Code para evoluir | Alta | Médio | Documentação completa na Fase 7; ADRs; código limpo |
| Não-reeleição em 2028 | Média | Variável | Dados exportáveis; sistema migrável; propriedade clara |
| Uso indevido em campanha | Baixa | Crítico | Sistema é para mandato; uso eleitoral exigirá filtragem + consentimento conforme momento |

---

## 7. Glossário

- **Demanda** — registro de uma necessidade ou pedido trazido ao mandato. Tem uma ou mais partes (pessoas e/ou entidades) ou é anônima.
- **Pessoa** — pessoa física que se relaciona com o mandato.
- **Entidade** — organização, coletivo ou agrupamento de qualquer natureza (formal ou informal) que se relaciona com o mandato.
- **Parte** — pessoa ou entidade vinculada a uma demanda específica.
- **Coordenação** — área funcional do gabinete (gabinete, jurídico, comunicação).
- **Encaminhamento** — comunicação a terceiro (órgão público, concessionária) feita a partir de uma demanda. Tem lifecycle próprio (enviado → respondido/vencido).
- **Inbox** — fila de itens capturados rapidamente, sem estrutura, aguardando triagem.
- **Interação** — registro pontual dentro de uma demanda. Pode estar no passado (`realizada`), no futuro (`agendada`), ou cancelada.
- **Interação automática** — gerada pelo sistema em mudanças da demanda. Imutável.
- **MPD** — Mandato Parlamentar Digital.
- **Origem responsiva / proativa** — responsiva nasce de uma necessidade trazida por pessoa; proativa nasce da iniciativa do mandato.
- **Tag tema** — tag vinculada à demanda como classificador de área temática. Critério de seleção definido na Fase 3 (ADR 0039).
- **Vínculo** — relação entre Pessoa e Entidade, com papel e período.

---

## 8. Como usar este roadmap no Claude Code

Este documento, junto com os outros em `docs/`, é a **fonte de verdade** do projeto.

Em cada sessão de Claude Code:

1. Ler `roadmap.md` e os documentos em `docs/` antes de qualquer ação.
2. Identificar a fase atual pela última tag Git.
3. Trabalhar **estritamente** no escopo da fase atual. Ideias para outras fases viram entradas em `decisoes.md` ou no backlog interno, não código fora de hora.
4. Para cada tarefa concluída, validar contra os critérios de aceite da fase.
5. Ao concluir uma fase, executar a suíte de validação automatizada antes de avisar Pedro para verificação manual.
6. Apenas após verificação manual de Pedro, criar a tag de versão e avançar.

**Pedro é o usuário final e o cliente.** Decisões técnicas (escolha de biblioteca, organização de código, refatorações) são responsabilidade do assistente. Pedro decide sobre produto, prioridades e UX.

**Princípio condutor de qualquer decisão técnica**: a solução mais simples que resolve o problema. Se uma solução parece complexa, provavelmente está atacando um problema que ainda não existe.

**Regra de ouro**: o código nunca vai além do que esses documentos definem. Se durante o desenvolvimento surgir necessidade não documentada, atualizar o documento **antes** de codar.

---

*Documento vivo. Última revisão: 2026-05-08, pós-Fase 2 (Pessoas, Entidades, Vínculos, Tags entregues).*
