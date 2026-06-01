# CLAUDE.md — Bússola para sessões com Claude Code

> Este arquivo é carregado automaticamente em toda sessão neste repositório. Mantenha curto, factual, fonte-de-verdade. Evolua a cada fase.

---

## 1. O que é o MPD

**Mandato Parlamentar Digital** — sistema de rastreabilidade de relacionamento político (categoria *constituent management*) para um mandato municipal. **Pessoa** é o núcleo; **demandas** orbitam a pessoa. Cada `Demanda` tem **dois eixos independentes**:

- `status` — ciclo de trabalho (`novo → em_andamento → respondido → arquivado`).
- `resultado` — desfecho material (`atendido | atendido_parcialmente | nao_atendido | inviavel | nao_se_aplica`).

**Regra de ouro do domínio:** demanda só vai para `respondida` com **retorno documentado** (data + conteúdo) **e** `resultado` classificado. Codificada no `clean()` do model — vale em qualquer porta de entrada.

**Multiplicidades:** demanda pode ter múltiplas pessoas e entidades como partes (M:N). Anexos são polimórficos — podem ser pendurados em Demanda, Pessoa, Entidade ou Encaminhamento.

---

## 2. Regra de ouro do projeto: documentação é fonte de verdade

Os documentos em [`docs/`](./docs/) e [`roadmap.md`](./roadmap.md) **são a fonte de verdade** do que o produto é. **Código nunca vai além da documentação.** Quando surge uma necessidade nova:

1. Atualizar o doc relevante (ou abrir uma ADR em `docs/decisoes.md`).
2. Validar com Pedro.
3. Só então codar.

Ideia que parece "óbvia" e não está no doc → primeiro vira ADR ou backlog.

---

## 3. Onde estão os docs

| Arquivo | Conteúdo |
|---|---|
| [`roadmap.md`](./roadmap.md) | Plano fase-a-fase (v0.1 → v6.x) com critérios de aceite. **Documento mais consultado.** |
| [`docs/modelo-de-dados.md`](./docs/modelo-de-dados.md) | Schema completo: entidades, campos, regras de validação, signals. |
| [`docs/mapa-de-telas.md`](./docs/mapa-de-telas.md) | Rotas, perfis que acessam, fluxos de navegação. |
| [`docs/permissoes.md`](./docs/permissoes.md) | Matriz de permissões por perfil/ação. |
| [`docs/fluxos-de-estado.md`](./docs/fluxos-de-estado.md) | Transições válidas de status, resultado, etc. |
| [`docs/decisoes.md`](./docs/decisoes.md) | ADRs cronológicas. Cada decisão arquitetural vira uma entrada aqui. |
| [`docs/debito-tecnico.md`](./docs/debito-tecnico.md) | Cheiros e refactors pendentes (`DT-NNN`). Por prioridade e gatilho de quando atacar. |
| [`docs/estrutura-do-repositorio.md`](./docs/estrutura-do-repositorio.md) | Organização de pastas, convenções, padrões de commit. |

---

## 4. Princípios operacionais

- **Produto sobre técnica.** Decisões técnicas servem o produto, não o contrário. Quando em dúvida, escolha a opção mais simples para o usuário final.
- **Fase a fase.** Não se adianta uma fase do roadmap para "ganhar tempo". Cada fase tem critério de aceite e é fechada com tag (`v0.1`, `v0.2`...).
- **Simplicidade vence.** Boring stack, padrões Django nativos, menos abstrações. `tests.py` único por app até apertar; `models/` virou pasta só quando passar de ~800 linhas.
- **Pedro é leigo em técnica.** Decisões técnicas são *do Claude*. Pedro decide produto. Quando uma escolha técnica afetar a experiência do usuário ou o roadmap, explicar trade-offs antes.
- **Idiomas:** código em **inglês**, domínio (modelos, campos, UI) em **português**. Ver `docs/estrutura-do-repositorio.md` §13.1.

---

## 5. Estado atual

**Fase corrente:** v0.7 — **Fase 6 (Segurança, Visualização, Exportação) concluída.** Filtros poderosos + exportação CSV nas listas principais; painel `/analise` com toggle tabela/gráfico (Chart.js CDN); auditoria UI `/auditoria` com diff visual; infra operacional (`/healthz`, `scripts/backup.sh`, `manage.py verificar_integridade`). LGPD foi **adiada para Fase 8 (v1.1)** — ADR 0047 documenta a decisão.

**Fundação (Fase 0/1, mantido):**
- Django 5.2 + PostgreSQL 16 + Tailwind v4 standalone.
- Settings split (`config/settings/{base,development,production,test}.py`).
- 4 apps: `core`, `accounts`, `pessoas`, `demandas`.
- `accounts.Usuario` (email como login), login/logout, sessão 12h / "lembrar-me" 30 dias, gestão de usuários, perfil.
- Política de senha: mínimo 8 chars, sem complexidade obrigatória (ADR 0023).

**Fase 2 (pessoas):**
- Models `Pessoa`, `Telefone`, `EmailPessoa`, `RedeSocial`, `Entidade`, `Vinculo`, `Tag`. Pessoa com endereço inline, validação de CPF, soft delete, anonimização. Contatos como entidades plurais (telefones, e-mails, redes sociais) — UI agrupa em seção "Contatos" com 3 sub-blocos dinâmicos. Validação por tipo: celular 11 dígitos com 9 após DDD, fixo 10 dígitos; rede social "Outro" exige rótulo. Pelo menos 1 canal de qualquer tipo é obrigatório. Ver ADR 0035 e ADR 0037.
- Entidade com 14 tipos (formais a `familia`/`grupo_informal`); CNPJ opcional UNIQUE NULLS DISTINCT.
- CRUDs com `PermissionRequiredMixin`, listas paginadas (25/pg), busca, filtros.
- ViaCEP em `pessoas/viacep.py` (tolerante a falha); deduplicação em `pessoas/deduplicacao.py`.
- Django Admin com fieldsets.
- 4 grupos padrão ("Administrador", "Chefe de Gabinete", "Coordenador", "Assessor") via data migration com permissões customizadas (`pode_desativar_*`, `pode_reativar_*`, `pode_anonimizar_pessoa`).
- ADR 0025: `BigAutoField` (supersede ADR 0002).

**Refactor de débito técnico (concluído na v0.3.2):**
- `core/utils.py` — formatação e validação de CPF/CNPJ/CEP/dígitos consolidadas. Resolve [DT-003](docs/debito-tecnico.md).
- `core/mixins.py` — `EnderecavelMixin` (7 campos de endereço) e `AuditavelMixin` (timestamps). Pessoa e Entidade herdam. Resolve [DT-002](docs/debito-tecnico.md).
- `pessoas/signals.py` — normalização via `pre_save` cobre todas as portas (ORM, Admin, Forms). Resolve [DT-001](docs/debito-tecnico.md).
- `Pessoa.anonimizar()` agora atômica (`@transaction.atomic`). Resolve [DT-004](docs/debito-tecnico.md).
- Migration `0001_initial` regenerada do zero (sem produção, ADR 0026).
- `slug_publico` (CharField hex de 12 chars, único, gerado por uuid4 no `pre_save`) implementado em Pessoa e Entidade — completa o trabalho de URLs com slug que estava parcial em views/urls/templates/tests.

**Hardening v0.3.1 (ADRs 0026–0033):**
- `DeduplicacaoCheckView` exige `view_pessoa` (fechou vazamento de PII) — ADR 0028.
- `auditlog` registra `Pessoa`, `Entidade`, `Vinculo`, `Tag`, `Telefone`, `EmailPessoa`, `RedeSocial` (LGPD) — ADR 0029, estendido em ADR 0037 para cobrir os canais plurais.
- `criar_usuarios_iniciais` exige `DEBUG=True` (anti-backdoor em prod) — ADR 0030.
- Toggle views padronizadas com `PermissionRequiredMixin` + `PermissionDenied` — ADR 0031.
- Rate limiting de login via `django-axes` (5 falhas / 30min, lockout por IP+username) — ADR 0032.
- `SECURE_PROXY_SSL_HEADER` env-driven, default off — ADR 0033.
- Identidade do mandato genérica em `.env.example` e docs (licenciabilidade) — ADR 0027.
- Tabela de credenciais permanece no `.env` local por escolha do proprietário — ADR 0026.
- Link `/admin/` removido da home pública.

**Polimento v0.3.2 (ADRs 0034–0039):**
- 4 flags LGPD (`nao_telefonar` etc.) removidas — YAGNI até newsletter (ADR 0034 supersede ADR 0012).
- `Telefone` como entidade própria 1:N com tipo (celular/fixo) e `eh_whatsapp` — ADR 0035.
- Geocodificação registrada como compromisso para v2.x junto com multi-endereço — ADR 0036.
- `EmailPessoa` e `RedeSocial` como entidades plurais sob seção "Contatos" — ADR 0037.
- `Tag.categoria` removida — agrupamento via tag plana é mais fluido (ADR 0039).
- Auditlog Correlation ID via middleware (`core/auditlog.py`) — cascata de delete aparece como conjunto único de LogEntries.
- UI: paleta de 11 cores fixas para Tag, fluxo de arquivar (não deletar), WhatsApp como ícone wa.me em listas, home autenticada com cards.
- fix: `PessoaForm` DateInput com `format="%Y-%m-%d"` — sem isso edição apagava `data_nascimento` silenciosamente.
- Comando `criar_dados_teste` para popular dev (idempotente, exige `DEBUG=True`).

**Limpeza pós-auditoria v0.3.3 (ADR 0040, DT-011/012):**
- `DeduplicacaoCheckView` JSON troca `id` por `slug_publico` — coerência com ADR 0038.
- `CEPLookupView` agora exige `view_pessoa` — fecha endpoint que estava só com login.
- `accounts.Usuario` registrado em auditlog (excluindo `password` e `last_login`) — fecha gap LGPD da gestão da equipe.
- `UsuarioUpdateForm` bloqueia auto-edição de `is_staff` (ADR 0040, mitigação tática).
- DT-011 registra refactor arquitetural pendente para gestão de usuários (Groups + permissão custom em `accounts`).
- DT-012 registra `create_user(password=None)` cria conta inutilizável silenciosamente.

**Fechamento de débito técnico v0.3.4 (DT-005, 006, 007, 008, 010, 012):**
- Unicidade de canais por pessoa: `UniqueConstraint` em Telefone(pessoa, numero), EmailPessoa(pessoa, endereco), RedeSocial(pessoa, plataforma, valor). Decisão de produto: rede social pode repetir handle em plataformas diferentes.
- Tailwind nos forms via `aplicar_tailwind()` em `pessoas/forms.py` — JS de injeção de classes removido dos 3 templates de form. Padrão herdável por Demanda.
- `pode_alternar_ativo` calculado nas DetailViews (Pessoa/Entidade) — templates simplificados.
- `_PessoaFormMixin.post()` em `transaction.atomic`: salva tudo, chama `pessoa.tem_meio_de_contato()`, rollback se falhar. Regra mora só no model.
- `create_user(password=None)` agora levanta `ValueError` em vez de criar conta sem login utilizável.
- DT-009 (toggle duplicado, YAGNI) e DT-011 (gestão usuários arquitetural, antes de produção) ficam adiados.

**100 testes passando** ao final da v0.3.4. ADRs 0001–0040 em [`docs/decisoes.md`](./docs/decisoes.md).

**Verificação de prontidão v0.3.5–v0.3.6:**
- `pytest`: 100/100 verde.
- `ruff` + `black`: limpo.
- `manage.py check`: sem issues.
- `manage.py makemigrations --check`: sincronizado (após gerar `accounts/0003_alter_usuario_managers` — registro do `UsuarioManager` no migration state, sem schema change).
- `criar_dados_teste`: idempotente, OK.
- Smoke test manual: criar pessoa, rollback de canal vazio (DT-008), unicidade de telefone (DT-010), Tailwind nos forms (DT-006), permissões de Assessor (DT-007). 5/5 ok.
- 2 fixes UX descobertos na verificação manual: botão "Cancelar" no form de Pessoa/Entidade volta para o detalhe quando editando (em vez de ir para a lista); template do form passa a renderizar `non_form_errors` dos formsets (erros tipo "duplicado" agora aparecem no topo).

**Polimento pré-Fase 3 (revisão de repo, v0.3.6):**
- `aplicar_tailwind` movido de `pessoas/forms.py` para `core/forms.py` — demandas/forms.py herda o mesmo helper.
- Dead code removido: `class="input"` em widgets de `accounts/forms.py` (templates do app renderizam HTML manual e ignoram widgets) e fallback `or self.kwargs.get("pk")` em `_PessoaFormMixin.post` (URLs sempre passam slug).
- `validate_cnpj_tamanho` ganha comentário explicando por que não valida DV (assimetria deliberada com CPF).
- `core/tests.py` deixa de ser placeholder: cobre `healthz`, `inicio` (anônimo vs autenticado) e `aplicar_tailwind` (idempotência).

**Fase 3 — Demandas e Interações (v0.4.0):**
- App `demandas` com `Demanda`, `DemandaPessoa`, `DemandaEntidade`, `Interacao`, `Encaminhamento`, `Anexo` (polimórfico via GenericForeignKey), `ItemInbox` (modelo só; UX em Fase 4).
- Demanda com 2 eixos independentes: `status` (novo→em_andamento→aguardando_*→respondido→arquivado) e `resultado` (pendente, atendido, parcial, não atendido, inviável, não se aplica). Regra de fechamento codificada em `clean()`: `respondido` exige retorno + resultado classificado. Resultado classificado não volta a pendente.
- Geração de número no formato `D-AAMM-NNNNN` (ADR 0056 — supersede `MPD-AAAA-NNNNN`): prefixo curto, ano+mês compactos, 5 dígitos aleatórios `10000–99999`. Retry com savepoint cobre colisão (padrão ADR 0051).
- Mudanças de status/responsável/resultado disparam **Interacao automática** via `post_save`. Snapshot de estado original em `__init__`. Middleware `UsuarioAtualMiddleware` repassa `request.user` para os signals.
- Schedule follow-up: ao salvar Interacao realizada, opcionalmente cria nova agendada com `interacao_origem` apontando para a anterior. Cadeia reconstruível.
- Janela de edição de 24h codificada em `Interacao.pode_editar`. Automáticas são imutáveis para todos. ADM/CG editam alheia.
- Encaminhamento com tipos de documento + status; resposta exige data + conteúdo. Reflete na timeline como interação manual.
- Anexo polimórfico com whitelist de mime + 25 MB. Limpeza de órfãos via `pre_delete` em Demanda/Pessoa/Entidade/Encaminhamento (GenericForeignKey não cascateia).
- Coordenação como atributo de `Usuario` (ADR 0041) — pré-requisito para regras de visibilidade restrita por coordenação.
- Permissões customizadas: `pode_arquivar_demanda`, `pode_arquivar_sem_responder`, `pode_marcar_restrita`, `pode_atribuir_responsavel`, `pode_reabrir_demanda`, `pode_excluir_demanda`, `pode_editar_interacao_alheia`, `pode_excluir_encaminhamento`. Distribuídas aos 4 grupos via `0002_grupos_padrao_demandas`.
- Auditlog: `Demanda`, `Encaminhamento`, `Anexo` registrados.
- Templates: lista com 8 quick filters (minhas, da minha coordenação, vencidas, sem retorno +30d, atendidas, não atendidas, sem resultado), detalhe com timeline cronológica + partes + encaminhamentos + anexos + bloco de Resultado inline + modais de "Marcar respondida" e "Arquivar". Formulário com formsets de partes (pessoas + entidades) e validação cross-objeto via `transaction.atomic` (padrão herdado de Pessoa).
- `criar_dados_teste` estendido com 2 demandas exemplo (responsiva + proativa).

**142 testes passando** ao final da v0.4.0 (37 novos no app `demandas` cobrindo os 22 critérios de aceite). ADRs 0001–0041.

**Redesign do fechamento da demanda (v0.4.2, ADR 0043):**
- Vocabulário polissêmico ("respondida" colidia com Encaminhamento e com retorno externo) eliminado: status `respondido` → **`concluida`**. Devolutiva ao demandante deixou de ser campo da Demanda e virou **Interação** (`tipo='devolutiva'`).
- Regra de fechamento bifurcada por origem em `Demanda.clean()`:
  - Responsiva: exige `Interacao(tipo=devolutiva, status=realizada)` vinculada **e** `resultado != pendente`.
  - Proativa: exige apenas `resultado != pendente`.
- UX: link discreto "Marcar como respondida" virou **CTA sólido** no topo do detalhe — **"Concluir demanda →"** em ambos os casos (proativa **continua sendo demanda**); o que diferencia é o sub-rótulo abaixo do botão: *"com devolutiva ao demandante"* (responsiva) vs *"origem proativa · sem devolutiva"* (proativa). Errata 2026-05-31 da ADR 0043 (rótulo original "Concluir ação" descartado por romper coerência conceitual). Modal centralizado pé-da-página virou **drawer lateral** (não cobre conteúdo, fecha por backdrop/Esc).
- `ConcluirDemandaView` orquestra tudo em `transaction.atomic`: cria Interacao(devolutiva), atualiza resultado/observação, muda status para `concluida`, roda `full_clean()` — rollback se qualquer passo falhar.
- Tipo `devolutiva` é exclusivo do fluxo de conclusão; não aparece no seletor genérico de "Adicionar interação" (evita devolutivas órfãs).
- Migration `0005_devolutiva_como_interacao` com data migration: para cada `Demanda.status='respondido'` com `retorno_data` preenchido, cria Interacao a partir dos campos `retorno_*` (com canal como prefixo do conteúdo), depois `UPDATE status='respondido' → 'concluida'`, depois drop dos campos.
- Quick filter `sem_retorno_30d` na lista vira "Sem devolutiva +30d" — agora busca por demandas responsivas abertas há +30d sem `Interacao(tipo=devolutiva)`.
- Permissões: labels atualizadas ("Pode arquivar demanda concluída", "Pode reabrir demanda concluída").

**148 testes passando** ao final da v0.4.2 (+6 sobre v0.4.0: novos casos cobrem responsiva sem devolutiva, responsiva com devolutiva + resultado pendente, responsiva concluída ok, proativa sem devolutiva ok, proativa sem resultado bloqueada). ADRs 0001–0043.

**Fase 4 — Visões Transversais (v0.5, em fechamento):**
- `/encaminhamentos/` como leitura agregada (filtros: status, órgão via autocomplete `<datalist>`, tipo de documento; quick filters: aguardando resposta, prazo vencido, respondidos esta semana). Cada linha é deep-link para a Demanda associada — **sem CRUD próprio nem detalhe próprio** (ADR 0046).
- Visibilidade do encaminhamento segue a da Demanda: `_filtrar_visiveis` aplicado antes de filtrar encaminhamentos.
- Quick filters operacionais novos:
  - `/demandas/`: "Com encaminhamento aberto", "Sem encaminhamento".
  - `/pessoas/` e `/entidades/`: "Com demanda em aberto".
- Topbar ganha link "Encaminhamentos" (entre Entidades e Configurações), gated por `demandas.view_encaminhamento`.
- `mapa-de-telas.md §8.10` documenta a nova rota.

**163 testes passando** ao final da v0.5 (+5 sobre v0.4.2). ADRs 0001–0046.

**Fase 5 — Inbox GTD e Minhas Pendências (v0.6):**
- Modelo `ItemInbox` (já existia desde Fase 3 sem UX) ganha UX completa.
- Captura rápida em 3 portas: atalho **Ctrl+K** em qualquer página, **FAB** fixo bottom-right (`+`), página standalone `/inbox/capturar/`. Modal global montado em `layouts/app.html`, JS minimalista (~50 linhas) sem dependência de framework. POST AJAX com `HX-Request` header, confirmação visual "Capturado!" 800ms antes de fechar.
- Lista `/inbox/` com filtros (pendentes/processados/descartados/todos). Badges de envelhecimento: âmbar +7d, vermelho +30d.
- Processamento `/inbox/<uuid>/processar/` em transação atômica: cria Demanda pré-preenchida com o conteúdo do item, valida formsets de partes + temas, marca item como processado com FK para a demanda gerada. Rollback se faltar parte em demanda não-anônima.
- Descarte `/inbox/<uuid>/descartar/` exige `motivo_descarte` (validação no model `clean()`).
- `/minhas-pendencias/` consolida `Interacao(autor=user, status=agendada)`, agrupadas por horizonte (Vencidas / Hoje / Amanhã / Esta semana / Próximas). Vencidas com borda vermelha no topo.
- `/minhas-reunioes/` herda da view de pendências filtrando `tipo=reuniao` próximos 30 dias.
- Topbar ganha links **Inbox** (com badge cinza do count de pendentes) e **Pendências** (com badge vermelho do count de vencidas). Context processor `core.context_processors.pendencias_usuario` popula esses contadores em todas as páginas autenticadas.
- Mapa-de-telas §4, §5 atualizado.

**171 testes passando** ao final da v0.6 (+8 sobre v0.5: captura simples, captura AJAX, processar cria demanda + marca item, descartar exige motivo, pendências do usuário, vencidas no topo, reuniões filtradas, context processor). ADRs 0001–0046.

**Fase 6 — Segurança, Visualização, Exportação (v0.7):**
- **Filtros + Exportação CSV** em `/demandas/`, `/pessoas/`, `/encaminhamentos/`. UTF-8 BOM + separador `;` (Excel BR). Limite 10k. Permissão CO+ (`_pode_exportar` em `demandas/views.py`). Cada exportação registra evento via `core.utils.registrar_export` (logger `mpd.exports`).
- **Painel `/analise`** (CG+ desde ADR 0055; era CO+ até v0.7.3) com 6 métricas: demandas por tema, por mês (últimos 12), por coordenação, top 20 pessoas, encaminhamentos pendentes por órgão, carga por assessor. Cada bloco tem **toggle tabela/gráfico** (Chart.js v4 via CDN — bar, line, doughnut).
- **Auditoria UI `/auditoria`** (ADM apenas desde ADR 0055; era CG+ até v0.7.3): lista paginada do `auditlog_logentry` com filtros (usuário, modelo, ação, período). Diff visual antes/depois por campo. `actor` pode ser `None` (eventos do sistema) — template trata.
- **`/healthz`** verifica conexão ao DB (retorna 503 se cursor.execute falha); público.
- **`scripts/backup.sh`** lê `.env`, prefere `DATABASE_URL`, fallback para variáveis individuais. Timestamp no nome do arquivo. Doc inline.
- **`manage.py verificar_integridade`** detecta 5 categorias: responsiva concluída sem devolutiva, anexo órfão (arquivo ou content_type), encaminhamento prazo passado com status=enviado, ItemInbox pendente +90d, Interação agendada +180d. Exit code 1 se encontrou problema (cron monitorado).
- **Topbar** ganha card "Auditoria" (ADM apenas, era CG+ — ADR 0055) e "Painel de análise" (CG+, era CO+ — ADR 0055) em `/configuracoes/`. Flags `papel_eh_admin`, `papel_eh_chefe`, `papel_eh_coordenador`, `papel_cg_plus`, `papel_co_plus` adicionados ao `context_processors.pendencias_usuario` para uso simples em templates.
- **LGPD adiada** para Fase 8 (v1.1) — ADR 0047 explica a decisão (LGPD obrigatória só com exposição pública; MVP é uso interno).

**179 testes passando** ao final da v0.7 (+8 sobre v0.6: CSV export OK, CSV bloqueia assessor, CSV respeita querystring, auditoria abre p/ admin, auditoria bloqueia coord, análise abre p/ coord, análise bloqueia assessor, verificar_integridade detecta devolutiva faltando). ADRs 0001–0047.

**UX polishings (v0.7.1):** topbar reordenada (Inbox primeiro); autocomplete server-side de Pessoa/Entidade (endpoints `*_buscar_json`); papel das partes (DemandaPessoa/DemandaEntidade) ganha choices com "Outro" + texto livre; popup AJAX para criar Tema in-line no form de demanda. **190 testes passando.**

**Fechamento de Fase 6 — segurança e robustez (v0.7.2):**
A revisão técnica de fim-de-Fase-6 (chefe de área Anthropic, 2026-05-17) identificou 5 gaps endereçados pelas ADRs 0048–0052:
- **Centralização de checagem de papel** ([core/permissoes.py](core/permissoes.py)) — `eh_cg_plus`/`eh_co_plus` substituem 11 ocorrências de `groups.filter(name__in=[...])`. ADR 0048 (resolve violação de ADR 0024).
- **Visibilidade de restritas no `/analise`** — manager `Demanda.objects.visiveis_para(user)`; 6 métricas + `top_pessoas` agora filtram corretamente. ADR 0049.
- **Auditlog estendido** para `Interacao` e `ItemInbox` — fecha rastreabilidade de edição de devolutiva e descarte de inbox. ADR 0050 (revisita 0029).
- **`slug_publico`** migrou de `pre_save` para `save()` com retry em IntegrityError dentro de savepoint — fecha TOCTOU. ADR 0051 (revisita 0038).
- **Robustez de signals** — `TIPO_DEVOLUTIVA` adicionado a `_TIPOS_INTERACAO_NAO_OPERACIONAIS`: conclusão de demanda em `novo` gera 1 transição, não 2 (timeline limpa).
- **Pequenos UX/perf** — `AnexoUploadView` retorna 404 (não 500) para objeto pai inexistente; `ProcessarInboxView` redireciona com mensagem em vez de 404 vazio; `_setup_anexos_orfaos` ganha handlers nomeados; `carga_assessores` em annotate única (elimina N+1); `PessoaCSVExport` usa cache de prefetch.
- **Deps**: `factory-boy` removido (zero uso); `django-htmx` mantido. ADR 0052.
- `pyproject.toml`: version `0.4.1` → `0.7.2`.

**207 testes passando** ao final da v0.7.2 (+17 sobre v0.7.1: 3 papel, 2 auditlog, 4 analise/restritas, 1 CSV regressão, 1 transição única, 1 slug retry, 1 anexo 404, 2 inbox conflito, 1 carga N+1, 1 CSV N+1). ADRs 0001–0052.

**Cobertura de critérios — Fases 4 a 6 (v0.7.3):**
A revisão de fim-de-Fase-6 levantou critérios literais do roadmap sem espelho na suíte. v0.7.3 fecha os preenchíveis e converte a entrega de auditoria de exports para o caminho visível na UI:
- **Exports em `/auditoria`** — `core.utils.registrar_export` migra de logger Python para `LogEntry(action=ACCESS)`. Logger mantido como linha de defesa. ADR 0053.
- **`verificar_integridade`** ganha cobertura nos 5 ramos que faltavam (anexo arquivo ausente, anexo órfão polimórfico, encaminhamento vencido com status=enviado, ItemInbox +90d, Interação agendada +180d) + sanity de base limpa.
- **Filtros em `/auditoria`** — testes confirmam usuário (email parcial), modelo (content_type), ação e período.
- **Cobertura de Fase 4/5**: `/entidades/` quick filter "com demanda em aberto", listagem `/inbox/` (default só pendentes; `?status=todos` inclui descartados; badges amber +7d / red +30d), fluxo "marcar realizada" a partir de `/minhas-pendencias/`.
- **UTF-8 BOM** já estava coberto em `test_export_csv_demandas_acessivel_a_coordenador` (v0.7) — apenas anotado.

**226 testes passando** ao final da v0.7.3 (+19 sobre v0.7.2: 3 export LogEntry, 6 verificar_integridade, 4 auditoria filtros, 1 entidades quick filter, 3 inbox lista, 2 minhas pendências). ADRs 0001–0053.

**Próximo marco:** v1.0 — Fase 7 (Polimento e Web). Ver [`roadmap.md`](./roadmap.md) §Fase 7.

---

## 6. Comandos úteis

```bash
# Setup inicial
uv sync --extra dev

# Servidor
uv run python manage.py runserver

# Migrações
uv run python manage.py makemigrations
uv run python manage.py migrate

# Superusuário
uv run python manage.py createsuperuser

# Testes
uv run pytest

# Lint + format
uv run ruff check . --fix
uv run black .

# Tailwind watch (recompila CSS automaticamente)
./bin/tailwindcss -i ./static/css/tailwind-input.css -o ./static/css/tailwind-output.css --watch
```

---

## 7. Convenções

- **Branches:** `main` (estável, com tags `v0.x`), `dev` (ativo), `feature/<nome-curto>`.
- **Commits:** Conventional Commits — `feat(casos):`, `fix(inbox):`, `docs(decisoes):`, `refactor`, `test`, `chore`. Escopo = nome do app afetado.
- **`tests.py` único por app** até passar de ~1500 linhas; aí vira pasta `tests/`.
- **Migrations:** geradas via `makemigrations -n <descricao>`. Nunca editadas manualmente após aplicadas (exceto data migrations).
- **Templates:** sempre estendem um layout (`base.html`, `layouts/auth.html`, `layouts/public.html`). Componentes via `{% include %}`.

---

## 8. O que NÃO está pronto (escopo entregue na Fase 0)

A Fase 0 deliberadamente **não** entrega:

- Modelos de domínio (`Pessoa`, `Demanda`, `DemandaPessoa`, `DemandaEntidade`, `Interacao`, `Encaminhamento`, `Anexo`, `ItemInbox`, `SolicitacaoLGPD`, `Tag`, `Entidade`, `Vinculo`) — `models.py` dos apps `cidadaos` e `casos` estão vazios (serão renomeados para `pessoas` e `demandas` antes da Fase 2).
- Login/logout customizado — **entregue na Fase 1**. Grupos Django (ADM/CG/CO/AS) e permissões por perfil — Fase 2 em diante, criados junto com os models que protegem.
- `core/permissions.py`, `core/middleware.py`, `core/templatetags/` — sem código de produto que os use ainda.
- `django-auditlog` instalado mas **sem registrar nenhum modelo** ainda — registros entram por modelo, fase a fase.
- HTMX/Alpine local — via CDN no MVP (Fase 6 considera baixar para `static/vendor/`).
- `Dockerfile`, CI/CD, deploy — Fase 6.

---

## 9. Pendência registrada para a próxima sessão (Fase 1)

**Decisão tomada (2026-05-08):** sistema de permissões modular via Django Groups + Permissions nativos. Ver ADRs 0022 e 0024.

- Grupos padrão criados na **Fase 2** (junto com `Pessoa`/`Entidade`) e expandidos na **Fase 3** (junto com `Demanda`). Fase 1 usa apenas `is_staff` para distinguir quem gerencia usuários.
- Toda verificação de permissão usa `user.has_perm()` — nunca checar nome de grupo diretamente no código.
- ADM pode criar/editar grupos sem deploy. A matriz documentada é configuração padrão, não regra de código.

**Apps renomeados (2026-05-08):** `cidadaos/` → `pessoas/`, `casos/` → `demandas/`. Django check e smoke tests passando.

---

## 10. Decisões técnicas registradas (resumo)

Para o histórico completo ver [`docs/decisoes.md`](./docs/decisoes.md). Decisões da Fase 0 que talvez mereçam ADR:

- **Tailwind standalone v4** (binário em `bin/`) em vez de `django-tailwind`. Razão: zero dependência de Node.js. Trade-off: cada dev baixa o binário (script no README).
- **`accounts.Usuario(AbstractUser)` desde a Fase 0**, mesmo sem campos extras. Razão: `AUTH_USER_MODEL` precisa ser definido antes da primeira `migrate`; trocar depois exige drop+recreate do banco.
- **SQLite in-memory para `pytest`** ([`config/settings/test.py`](./config/settings/test.py)). Razão: testes da Fase 0 não dependem de features Postgres-only; evita acoplar `pytest` ao banco rodando. Quando a suíte usar JSONB, full-text, etc., migrar para Postgres em testes.
- **`uv sync --extra dev`** (não `[dependency-groups]`). Razão: fidelidade ao esboço em `docs/estrutura-do-repositorio.md` §12.

---

*Atualizar este arquivo ao fim de cada fase. Última atualização: 2026-05-17 (v0.7.3 — cobertura de testes dos critérios de Fases 4 a 6; exports visíveis em `/auditoria` via ADR 0053).*
