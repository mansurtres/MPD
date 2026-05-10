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

### DT-005 — Early-return defensivo em `_PessoaFormMixin.post()`

**Prioridade:** Decisão pendente
**Sintoma:** [pessoas/views.py:116-121](pessoas/views.py#L116-L121) detecta POST sem `TOTAL_FORMS` e redireciona com flash. Comentário cita "template velho em cache, resubmit do navegador". Teste correspondente ([pessoas/tests.py:433-440](pessoas/tests.py#L433-L440)) só verifica 302, não distingue do 302 de sucesso.
**Por que é cheiro:** combate sintoma sem documentar a causa. Casuístico.
**Proposta:** **decidir** — ou (a) remover e deixar `ManagementForm` virar `form_invalid` normal, ajustando o teste; ou (b) manter e abrir ADR explicando o cenário concreto que motivou.
**Gatilho:** próxima sessão de revisão de Pessoas. Decisão simples.

### DT-006 — JavaScript injetando classes Tailwind em runtime

**Prioridade:** Média
**Sintoma:** [templates/pessoas/form.html:342-347](templates/pessoas/form.html#L342-L347) faz `el.classList.add("w-full", ...)` em todos os inputs renderizados pelo Django.
**Por que é cheiro:** vaza a fonte de verdade do estilo. Frágil se purge do Tailwind mudar; quebra silenciosamente se outro template renderizar o mesmo form.
**Proposta:** mover classes para `widget=forms.TextInput(attrs={"class": "..."})` nos forms. Alternativa: `django-widget-tweaks`.
**Gatilho:** quando criar o segundo form que sofra do mesmo padrão (provavelmente em Demanda).

### DT-007 — Condicional ambígua em `detalhe.html`

**Prioridade:** Média
**Sintoma:** [templates/pessoas/detalhe.html:20](templates/pessoas/detalhe.html#L20):
```django
{% if pessoa.ativo and perms...pode_desativar_pessoa or not pessoa.ativo and perms...pode_reativar_pessoa %}
```
**Por que é cheiro:** funciona por precedência (`and` antes de `or`), mas é o tipo de linha que se mexe e quebra.
**Proposta:** empurrar para a view (`ctx["pode_alternar_ativo"] = ...`) ou quebrar com `{% with %}`.
**Gatilho:** quando esse padrão aparecer pela 2ª vez.

### DT-008 — Regra "exige um canal" duplicada entre model e view

**Prioridade:** Média
**Sintoma:** [pessoas/models.py:210-214](pessoas/models.py#L210-L214) tem `tem_meio_de_contato()`, mas [pessoas/views.py:126-135](pessoas/views.py#L126-L135) re-implementa a regra checando os formsets antes do save.
**Por que é cheiro:** regra de produto mora em dois lugares; mudança em uma não pega a outra.
**Proposta:** view salva tudo em transação, chama `pessoa.full_clean()` (que invoca `clean()` que verifica `tem_meio_de_contato()`); se falhar, rollback + mostra erro.
**Gatilho:** quando a regra de canal mudar (ex: WhatsApp obrigatório para certas categorias).

### DT-009 — `PessoaToggleAtivoView` ≡ `EntidadeToggleAtivoView`

**Prioridade:** Baixa
**Sintoma:** [pessoas/views.py:191-210](pessoas/views.py#L191-L210) e [pessoas/views.py:331-348](pessoas/views.py#L331-L348) são quase idênticas, trocando "pessoa" por "entidade".
**Proposta:** `ToggleAtivoView` paramétrico. Mas YAGNI com 2 ocorrências.
**Gatilho:** **3ª ocorrência** (Demanda? Tag?). Antes disso, deixar.

### DT-010 — Unicidade de canais por pessoa (pergunta de produto)

**Prioridade:** A definir com Pedro
**Sintoma:** `EmailPessoa` permite duas linhas com mesmo `(pessoa, endereco)` (rótulos diferentes). `Telefone` permite duas linhas com mesmo `(pessoa, numero, tipo)`.
**Por que pode ser cheiro:** se for dado intencional (mesmo telefone, rótulos "trabalho"/"recado"), está certo. Se foi descuido, abre porta para duplicatas silenciosas.
**Proposta:** definir com Pedro se quer `unique_together` (ou `UniqueConstraint`) para esses pares. Decidir antes de subir produção.
**Gatilho:** próxima conversa de produto.

---

## Accounts (Fase 1)

### DT-011 — Gestão de usuários ainda usa `is_staff`, não Groups (arquitetural)

**Prioridade:** Alta antes de produção, Média antes de Fase 4
**Sintoma:** [accounts/views.py:13-19](accounts/views.py#L13-L19) define `StaffRequiredMixin` que gata as views de gestão de usuário em `request.user.is_staff`. [accounts/forms.py:36](accounts/forms.py#L36) e [:63](accounts/forms.py#L63) incluem `is_staff` como campo editável em `UsuarioCreateForm` e `UsuarioUpdateForm`.
**Por que é cheiro:** o app `pessoas` migrou para `PermissionRequiredMixin` + Django Groups (ADR 0024) na Fase 2. O app `accounts` ficou para trás — ainda usa o flag binário `is_staff`. Resultado: qualquer staff promove qualquer outro a staff via formulário. Em equipe pequena confiável (caso atual), risco baixo. Mas viola o modelo de permissões granular adotado e gera dois sistemas convivendo no mesmo projeto.
**Proposta:** criar permissão customizada `accounts.gerenciar_usuarios` (ou similar); migrar `UsuarioListView`/`CreateView`/`UpdateView`/`ToggleAtivoView` para `PermissionRequiredMixin` com essa permissão; adicionar a permissão ao grupo `Administrador`; remover `StaffRequiredMixin`. Forms deixam de expor `is_staff` editável (continuam expondo `is_active`); promoção a staff/superuser passa a ser ação reservada via Django Admin. Mitigação tática (commit `<sha>`, ADR 0040) bloqueia self-edit; o fix arquitetural fecha o resto.
**Gatilho:** **antes de produção** ou **antes de adicionar mais views em accounts** (o que vier primeiro).

### DT-012 — `accounts.Usuario` validação fraca permite criar usuário com senha vazia via ORM

**Prioridade:** Baixa
**Sintoma:** `UsuarioManager.create_user(email, password=None, ...)` chama `set_password(None)`, que cria conta com senha inutilizável (não vazia, mas hash inválido). Funcional, mas inconsistente com `create_superuser` que aceita os mesmos defaults.
**Por que é cheiro:** silêncio em vez de erro. Se alguém criar via shell sem passar password, vira fantasma sem login.
**Proposta:** `if password is None: raise ValueError("Senha é obrigatória.")` em `create_user`.
**Gatilho:** próxima refactor de `accounts`.

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
