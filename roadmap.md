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
- `v0.5` — Fase 4: Inbox GTD + Minhas Pendências
- `v0.6` — Fase 5: Análise, Auditoria, LGPD
- `v1.0` — Fase 6: Polimento e Web

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

- [ ] `python manage.py runserver` inicia sem erros.
- [ ] `http://localhost:8000/` retorna página estilizada.
- [ ] `python manage.py migrate` sem erros.
- [ ] `python manage.py createsuperuser` funciona.
- [ ] `pytest` passa.
- [ ] `ruff check .` e `black --check .` passam.
- [ ] README permite clonar e rodar do zero.
- [ ] Tag `v0.1` no GitHub.

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

- [ ] URL não pública redireciona para login.
- [ ] Usuário consegue logar e fazer logout.
- [ ] Usuário `is_staff` consegue criar/editar/desativar outros usuários.
- [ ] Usuário sem `is_staff` recebe 403 ao tentar gerenciar usuários.
- [ ] Senhas fracas rejeitadas.
- [ ] `criar_usuarios_iniciais` funciona.
- [ ] Logout invalida sessão.

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
1. App `pessoas` com modelos: `Pessoa`, `Entidade`, `Vinculo`, `Tag`.
2. **Endereço inline** em `Pessoa` e `Entidade`.
3. **Preferências de comunicação** em `Pessoa`: 4 booleans (`nao_telefonar`, `nao_enviar_email`, `nao_enviar_sms`, `nao_compartilhar_dados`).
4. **Campos extras de canal:** `whatsapp` e `instagram` em Pessoa.
5. Validações: pelo menos um entre email/telefone/whatsapp; bairro/cidade obrigatórios; CPF válido por algoritmo.
6. **Integração ViaCEP**: módulo `pessoas/viacep.py`. Tolerante a falha.
7. **Deduplicação**: CPF UNIQUE NULLS DISTINCT; alerta AJAX por similaridade em email/telefone/whatsapp.
8. Tags com 4 categorias (`tema`, `perfil`, `territorio`, `livre`).
9. Telas conforme `docs/mapa-de-telas.md` (seções 6 e 7).
10. **Criar grupos padrão** (Administrador, Chefe de Gabinete, Coordenador, Assessor) via data migration com as permissões dos models desta fase. Permissões de `demandas` adicionadas na Fase 3. Matriz completa em `docs/permissoes.md`.
11. Soft delete via campo `ativo`.
12. Django Admin com fieldsets organizados.

#### 4.2.3. Critérios de Aceite

- [ ] Renomear apps concluído; migrate sem erros.
- [ ] Cadastrar pessoa completa, sem demanda, funciona.
- [ ] Cadastro sem email/telefone/whatsapp rejeitado com mensagem clara.
- [ ] CEP válido auto-preenche endereço.
- [ ] CPF duplicado bloqueado.
- [ ] Email/telefone duplicado mostra alerta amarelo, mas permite criar.
- [ ] Preferências de comunicação salvam e são exibidas no detalhe.
- [ ] Lista pagina, busca, filtra.
- [ ] Cadastrar entidade (inclusive tipo `familia` ou `grupo_informal`) e vincular pessoa funciona.
- [ ] Tag criada e atribuída.
- [ ] Permissões respeitadas por perfil.
- [ ] Soft delete remove de listagem mas preserva no banco.

#### 4.2.4. Validação

```bash
pytest pessoas/ -v --cov=pessoas
```

#### 4.2.5. Verificação Manual

1. Cadastrar 5 pessoas com variações.
2. Tentar duplicado e ver alerta.
3. Cadastrar "Família Silva" como Entidade tipo `familia` e vincular 3 pessoas.
4. Cadastrar associação fictícia com CNPJ e vincular pessoas.
5. Marcar `nao_enviar_email` em uma pessoa.
6. Criar tags e atribuir.
7. Buscar por nome, bairro, tag.
8. Logar como diferentes perfis e verificar permissões.
9. Desativar pessoa.

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
4. **Geração de número** thread-safe. Formato `MPD-AAAA-NNNNN`.
5. **Tema da demanda** = uma tag de categoria `tema` vinculada via M:N.
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

- [ ] Criar demanda vinculando múltiplas pessoas funciona.
- [ ] Criar demanda anônima funciona com flag.
- [ ] Criar demanda vinculada apenas a entidade funciona.
- [ ] Demanda recém-criada tem `resultado='pendente'` por default.
- [ ] Mudar status para "respondido" sem retorno → bloqueado.
- [ ] Mudar status para "respondido" com `resultado='pendente'` → bloqueado com mensagem clara.
- [ ] Atualizar `resultado` em qualquer status da demanda funciona.
- [ ] Mudança de `resultado` gera interação automática `mudanca_resultado` na timeline.
- [ ] Adicionar interação `realizada` registra na timeline.
- [ ] Adicionar interação `agendada` (com data futura) aparece em "minhas pendências".
- [ ] Schedule Follow-up: ao encerrar interação, oferta cria follow-up agendado.
- [ ] Cadeia de follow-up reconstrutível via `interacao_origem_id`.
- [ ] Mudar status da demanda gera interação automática na timeline.
- [ ] Mudar responsável gera interação automática.
- [ ] Interação `automatica=TRUE` é imutável (não editável por ninguém).
- [ ] Janela de 24h: editar interação própria recém-criada funciona; após 24h, bloqueada.
- [ ] Adicionar encaminhamento aparece na timeline.
- [ ] Anexo pendurado na Demanda aceito; anexo pendurado no Encaminhamento aceito.
- [ ] Anexo de 30MB rejeitado; de 5MB aceito.
- [ ] Detalhe da pessoa lista todas as demandas vinculadas.
- [ ] Filtro "Minhas demandas" funciona.
- [ ] Demanda restrita não aparece para CO de outra coordenação.

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

### Fase 4 — Inbox GTD e Minhas Pendências

**Versão:** `v0.5`
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

- [ ] `Ctrl+K` em qualquer página abre modal.
- [ ] Texto enviado vira `ItemInbox` pendente.
- [ ] Modal fecha sem perder contexto da página anterior.
- [ ] Badge de pendências vencidas aparece na topbar.
- [ ] Lista `/inbox` mostra pendentes com indicadores visuais.
- [ ] Processar gera caso e marca item processado.
- [ ] Caso gerado tem conteúdo do item como descrição inicial.
- [ ] Descartar pede motivo e registra.
- [ ] `/minhas-pendencias` lista todas as interações agendadas do usuário.
- [ ] Pendências vencidas aparecem em vermelho no topo.
- [ ] Marcar pendência como realizada (a partir de "minhas pendências") funciona.
- [ ] `/minhas-reunioes` filtra apenas tipo `reuniao`.

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

### Fase 5 — Análise, Auditoria, LGPD

**Versão:** `v0.6`
**Objetivo:** robustez e responsabilidade. Filtros poderosos, exportações, auditoria, LGPD, gestão da equipe.

#### 4.5.1. Pré-requisitos

Fase 4 concluída.

#### 4.5.2. Especificações

1. **Filtros avançados** em todas as listagens via querystring.
2. **Exportação CSV**: UTF-8 com BOM, separador `;` (Excel BR). Permissão CO+. Limite 10.000 registros. Toda exportação registrada.
3. **Painel `/analise`** (CO+):
   - Cidadãos por bairro.
   - Casos por tema.
   - Casos por mês (textual).
   - Top 50 cidadãos com mais casos.
   - Encaminhamentos pendentes por órgão.
   - **Carga por assessor** (casos abertos, vencidos, tempo médio de resposta).
4. **Auditoria via `django-auditlog`**: configurar nos modelos críticos. View `/auditoria` (CG+) com diff visual.
5. **LGPD**:
   - Página `/privacidade` (público).
   - Formulário `/privacidade/solicitar` (público, com rate limiting).
   - Modelo `SolicitacaoLGPD` em `accounts/models.py`.
   - Lista interna `/configuracoes/lgpd` (CO+).
   - Geração de relatório PDF dos dados de um cidadão (CO Jurídico, CG, ADM).
   - Anonimização de cidadão.
6. **Health check** `/healthz`.
7. **Backup**: `scripts/backup.sh`.
8. **Verificação de integridade**: comando `manage.py verificar_integridade`.

#### 4.5.3. Critérios de Aceite

- [ ] Filtros combinam via querystring corretamente.
- [ ] CSV abre no Excel BR com acentuação.
- [ ] Exportação registra log de auditoria.
- [ ] Listagens analíticas carregam em < 1s para 1000 registros.
- [ ] Painel "Carga por assessor" funciona.
- [ ] Editar cidadão registra log com diff.
- [ ] Tentar editar log → bloqueado.
- [ ] Caso "restrito" não aparece para CO de outra coordenação.
- [ ] `/privacidade` acessível sem login.
- [ ] Solicitação LGPD pública gera item na fila.
- [ ] Relatório PDF de dados do cidadão gerado.
- [ ] Anonimizar preserva contagens históricas mas remove identificadores.
- [ ] Rate limiting bloqueia 11ª submissão em 1 minuto.
- [ ] `backup.sh` gera dump válido.
- [ ] `verificar_integridade` detecta inconsistências.
- [ ] `/healthz` retorna 200.

#### 4.5.4. Validação

```bash
pytest -v --cov
python manage.py verificar_integridade
bash scripts/backup.sh /tmp/test-backup
```

#### 4.5.5. Verificação Manual

1. Filtrar cidadãos por bairro + tag, exportar CSV. Abrir no Excel.
2. Como CG, ver "Carga por assessor" e identificar quem tem mais casos.
3. Editar cidadão e ver log em `/auditoria`.
4. Marcar caso como restrito; testar acesso de outras coordenações.
5. Acessar `/privacidade` deslogado.
6. Submeter solicitação LGPD pública.
7. Como CO Jurídico, processar. Gerar relatório PDF.
8. Anonimizar cidadão de teste; ver casos históricos preservados.
9. Rodar `backup.sh`.

---

### Fase 6 — Polimento e Web

**Versão:** `v1.0`
**Objetivo:** sistema pronto para uso interno do gabinete e deploy.

#### 4.6.1. Pré-requisitos

Fase 5 concluída.

#### 4.6.2. Especificações

1. **UX**: revisão mobile (320–768px), empty states, mensagens claras, confirmações modais.
2. **Documentação**: `docs/manual.md` (manual de uso para a equipe), `docs/deploy.md`.
3. **Configuração de produção**: `production.py` revisado, Whitenoise, logging estruturado, Sentry opcional.
4. **Docker**: `Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`.
5. **Performance**: auditoria de queries, `select_related`/`prefetch_related`, gzip.
6. **Acessibilidade básica**: contraste WCAG AA, navegação por teclado, `aria-label`.
7. **Compatibilidade**: Chrome, Firefox, Safari, Edge (últimas 2 versões).
8. **Limpeza**: remover código morto, atualizar dependências.

#### 4.6.3. Critérios de Aceite

- [ ] Telas funcionam em smartphone.
- [ ] Manual revisado por um assessor leigo.
- [ ] `docker compose up` sobe ambiente de desenvolvimento.
- [ ] Documentação de deploy permite hospedar em VPS em <2h.
- [ ] Lighthouse: Performance ≥ 85, Accessibility ≥ 90.
- [ ] Sem warnings no console.
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

## 5. Pós-MVP — Roadmap de Evolução

A partir de `v1.0`, evolução guiada por uso real.

### v1.x — Refinamentos
- Engagement Score por cidadão (pontuação automática a partir das interações).
- Smart Groups (filtros nomeados que se atualizam sozinhos).
- Notificações por e-mail (caso atribuído, prazo próximo, retorno recebido).
- Dashboards visuais (Chart.js).
- Importação em lote via CSV.
- Newsletter para a base (respeitando communication preferences).

### v2.x — Mandato
- **Proposições legislativas** (PL, RI, indicação, moção) com vínculo N:N a casos.
- **Agenda do mandato** como módulo dedicado, com calendário visual e integração Google Calendar.
- **Multi-endereço** por cidadão.
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
| Performance degrada com base grande | Média | Médio | Índices bem definidos; paginação; otimização na Fase 6 |
| Vazamento de dados | Baixa | Crítico | Auditoria desde Fase 5; hospedagem BR; backup criptografado |
| Demanda LGPD inesperada | Média | Alto | Política definida na Fase 5; controlador identificado |
| Pedro fica dependente de Claude Code para evoluir | Alta | Médio | Documentação completa na Fase 6; ADRs; código limpo |
| Não-reeleição em 2028 | Média | Variável | Dados exportáveis; sistema migrável; propriedade clara |
| Uso indevido em campanha | Baixa | Crítico | Sistema é para mandato; uso eleitoral exigirá filtragem + consentimento conforme momento |

---

## 7. Glossário

- **Demanda** — registro de uma necessidade ou pedido trazido ao mandato. Tem uma ou mais partes (pessoas e/ou entidades) ou é anônima.
- **Pessoa** — pessoa física que se relaciona com o mandato (solicitante, afetada, representante, etc.).
- **Entidade** — organização, coletivo ou agrupamento de qualquer natureza (formal ou informal) que se relaciona com o mandato.
- **Parte** — pessoa ou entidade vinculada a uma demanda específica, com um papel (solicitante, afetada, representante, etc.).
- **Coordenação** — área funcional do gabinete (gabinete, jurídico, comunicação).
- **Encaminhamento** — comunicação a terceiro (órgão público, concessionária) feita a partir de uma demanda. Tem lifecycle próprio (enviado → respondido/vencido).
- **Inbox** — fila de itens capturados rapidamente, sem estrutura, aguardando triagem.
- **Interação** — registro pontual dentro de uma demanda. Pode estar no passado (`realizada`), no futuro (`agendada`), ou cancelada.
- **Interação automática** — gerada pelo sistema em mudanças da demanda. Imutável.
- **MPD** — Mandato Parlamentar Digital.
- **Origem responsiva / proativa** — responsiva nasce de uma necessidade trazida por pessoa; proativa nasce da iniciativa do mandato.
- **Tag tema** — tag de categoria `tema`, usada para classificar a área temática da demanda.
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
