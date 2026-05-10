# MPD — Débito técnico

Itens identificados que **funcionam** mas merecem refactor antes de virarem problema. Não são bugs nem cheiros sob suspeita: são pontos onde o código pode ser mais limpo, mais hígido, ou onde uma decisão precisa ser tomada.

> **Por que existe este documento:** ADR é decisão tomada; roadmap é fase-a-fase de produto. Débito técnico é a categoria intermediária — coisas reconhecidas, pendentes, transversais, com prioridade declarada e gatilho de quando atacar.

## Como ler

Cada item tem:
- **ID** (`DT-NNN`) — referência fixa para usar em commit/PR.
- **Prioridade** — Alta (atacar antes da próxima fase), Média (quando incomodar), Baixa (deixar para quando o sistema crescer).
- **Sintoma** — o que se observa hoje no código.
- **Por que é cheiro** — por que isso pode virar problema.
- **Proposta** — direção sugerida (não obrigatória).
- **Gatilho** — quando atacar.

Quando um item for resolvido, mover para a seção **Resolvidos** no fim com a referência ao commit/ADR.

---

## Pessoas (Fase 2)

### DT-009 — `PessoaToggleAtivoView` ≡ `EntidadeToggleAtivoView`

**Prioridade:** Baixa
**Sintoma:** [pessoas/views.py:191-210](pessoas/views.py#L191-L210) e [pessoas/views.py:331-348](pessoas/views.py#L331-L348) são quase idênticas, trocando "pessoa" por "entidade".
**Proposta:** `ToggleAtivoView` paramétrico. Mas YAGNI com 2 ocorrências.
**Gatilho:** **3ª ocorrência** (Demanda? Tag?). Antes disso, deixar.

---

## Accounts (Fase 1)

### DT-011 — Gestão de usuários ainda usa `is_staff`, não Groups (arquitetural)

**Prioridade:** Alta antes de produção, Média antes de Fase 4
**Sintoma:** [accounts/views.py:13-19](accounts/views.py#L13-L19) define `StaffRequiredMixin` que gata as views de gestão de usuário em `request.user.is_staff`. [accounts/forms.py:36](accounts/forms.py#L36) e [:63](accounts/forms.py#L63) incluem `is_staff` como campo editável em `UsuarioCreateForm` e `UsuarioUpdateForm`.
**Por que é cheiro:** o app `pessoas` migrou para `PermissionRequiredMixin` + Django Groups (ADR 0024) na Fase 2. O app `accounts` ficou para trás — ainda usa o flag binário `is_staff`. Resultado: qualquer staff promove qualquer outro a staff via formulário. Em equipe pequena confiável (caso atual), risco baixo. Mas viola o modelo de permissões granular adotado e gera dois sistemas convivendo no mesmo projeto. Mitigação tática (commit `c216150`, ADR 0040) bloqueia self-edit de `is_staff` no form custom; o `/admin/auth/user/` continua aceitando.
**Proposta:** criar permissão customizada `accounts.gerenciar_usuarios` (ou similar); migrar `UsuarioListView`/`CreateView`/`UpdateView`/`ToggleAtivoView` para `PermissionRequiredMixin` com essa permissão; adicionar a permissão ao grupo `Administrador`; remover `StaffRequiredMixin`. Forms deixam de expor `is_staff` editável (continuam expondo `is_active`); promoção a staff/superuser passa a ser ação reservada via Django Admin. O fix arquitetural fecha o resto.
**Gatilho:** **antes de produção** ou **antes de adicionar mais views em accounts** (o que vier primeiro).

---

## Resolvidos

### DT-001 — Normalização vazada entre `clean()` e `save()` em Pessoa/Entidade

**Resolvido em:** 2026-05-09 (v0.3.2).
**Como:** normalização movida para `pessoas/signals.py` (`pre_save`) — cobre 100% das portas (ORM, Admin, Forms, scripts). `validators=[validate_cpf]` adicionado no campo `Pessoa.cpf`; análogos para `validate_cnpj_tamanho` em `Entidade.cnpj` e `validate_cep`/`UF_VALIDATOR` no `EnderecavelMixin`. `clean()` de Pessoa e Entidade removidos (regra de negócio absorvida pelos validators).

### DT-002 — Endereço duplicado entre Pessoa e Entidade

**Resolvido em:** 2026-05-09 (v0.3.2).
**Como:** criados `EnderecavelMixin` e `AuditavelMixin` em [core/mixins.py](core/mixins.py). Pessoa redeclara `bairro`/`cidade` como obrigatórios e `estado` com default `"ES"`. `criado_por` permanece em cada subclasse para preservar `related_name` específico (`pessoas_criadas`/`entidades_criadas`). Migration `0001_initial` regenerada do zero (banco sem produção, ADR 0026/feedback `refazer_vs_migrar`).

### DT-003 — `re.sub(r"\D", "", ...)` duplicado em 5+ pontos

**Resolvido em:** 2026-05-09 (v0.3.2).
**Como:** consolidado em [core/utils.py](core/utils.py): `somente_digitos`, `formatar_cep`, `formatar_cpf`, `formatar_cnpj`, `validate_cpf`, `validate_cnpj_tamanho`, `validate_cep`. Imports atualizados em `pessoas/models.py`, `pessoas/deduplicacao.py`, `pessoas/viacep.py`, `pessoas/signals.py`, `pessoas/tests.py`.

### DT-004 — `Pessoa.anonimizar()` sem transação

**Resolvido em:** 2026-05-09 (v0.3.2).
**Como:** decorador `@transaction.atomic` em `Pessoa.anonimizar()`. Save da pessoa e deletes de canais agora são tudo-ou-nada.

### DT-005 — Early-return defensivo em `_PessoaFormMixin.post()`

**Resolvido em:** 2026-05-10 (v0.3.4).
**Como:** mantido. Comentário reescrito explicitando o cenário concreto (aba aberta antes de deploy que mudou template, ou submit duplicado do navegador). Sem isso, o erro genérico do Django sobre `ManagementForm` aparece ao usuário, sem ação clara. Mensagem amigável e redirect para GET limpo é melhor UX.

### DT-006 — JavaScript injetando classes Tailwind em runtime

**Resolvido em:** 2026-05-10 (v0.3.4).
**Como:** função `aplicar_tailwind(form)` em [pessoas/forms.py](pessoas/forms.py) injeta classes Tailwind nos widgets via `__init__` de cada form (idempotente, detecta tipo de widget). Removidos os `classList.add(...)` de `templates/pessoas/form.html`, `templates/pessoas/entidades/form.html`, `templates/pessoas/tags/form.html`. Estilo agora vem do Python (fonte única) — Demanda herda o padrão automaticamente.

### DT-007 — Condicional ambígua em `detalhe.html`

**Resolvido em:** 2026-05-10 (v0.3.4).
**Como:** `pode_alternar_ativo` calculado em `PessoaDetailView.get_context_data` e `EntidadeDetailView.get_context_data`. Templates passam a usar `{% if pode_alternar_ativo %}` — uma variável, sem precedência ambígua. Padrão herdável por Demanda quando precisar de transição condicionada a permissão.

### DT-008 — Regra "exige um canal" duplicada entre model e view

**Resolvido em:** 2026-05-10 (v0.3.4).
**Como:** `_PessoaFormMixin.post()` agora salva form + formsets em `transaction.atomic()`, depois chama `self.object.tem_meio_de_contato()` (regra única, no model); se falhar, `transaction.set_rollback(True)` reverte tudo e re-renderiza o form com erro. View deixou de re-implementar a regra. Padrão correto para Fase 3 (Demanda tem regra cross-objeto análoga: `respondida` exige retorno + resultado classificado).

### DT-010 — Unicidade de canais por pessoa

**Resolvido em:** 2026-05-10 (v0.3.4).
**Como:** decisão de produto tomada (não faz sentido mesma pessoa ter telefone/e-mail duplicado; rede social pode ter mesmo handle em plataformas diferentes). `UniqueConstraint` adicionado em `Telefone(pessoa, numero)`, `EmailPessoa(pessoa, endereco)` e `RedeSocial(pessoa, plataforma, valor)`. Migration `0003_unicidade_canais`. Mensagens de erro customizadas via `violation_error_message`. Normalização (signals) garante que comparações funcionam mesmo com formatação variada na entrada.

### DT-012 — `create_user(password=None)` cria usuário fantasma silenciosamente

**Resolvido em:** 2026-05-10 (v0.3.4).
**Como:** `UsuarioManager.create_user` agora levanta `ValueError("Senha é obrigatória...")` quando `password` é falsy. `create_superuser` continua funcionando porque sempre passa senha explícita. Teste de regressão em `accounts/tests.py`.
