# MPD — Matriz de Permissões (v2 · need-to-know)

Documento consolidado das regras de acesso e visibilidade do sistema. Define quem vê, cria, edita e exclui cada entidade — e, sobretudo, **o que cada papel NÃO vê**.

> **Princípio (ADR 0059): privilégio mínimo / need-to-know.** Cada usuário vê apenas o que precisa para operar **agora**. Inverte o princípio anterior ("colaborativo por default"). Motivo: o risco de exfiltração da base inteira é incomparavelmente maior que o de um vazamento pontual. Reduzir a superfície de leitura é a defesa principal.

> **Sobre este documento:** descreve a **configuração padrão** dos grupos (Django Groups + Permissions nativos, ADR 0022/0024). O Admin pode ajustar sem mexer em código, mas a matriz abaixo é a regra que o sistema entrega de fábrica e que a implementação garante em três camadas (template, view, manager/QuerySet).

---

## 1. Perfis

Três perfis na v1, atribuídos via Django Group. Cada usuário pertence a exatamente um. **Não há mais "Coordenador" nem campo de "coordenação" (time)** — removidos na ADR 0059 (o papel ficaria oco sem o conceito de time).

| Perfil | Quem é | Quantidade típica |
|---|---|---|
| **Administrador** (`ADM`) | Pedro (vereador, dono do sistema) | 1 |
| **Chefe de Gabinete** (`CG`) | Coordenação política geral — camada de gestão operacional | 1 |
| **Assessor** (`AS`) | Demais assessores parlamentares | 4–10 |

> Papéis futuros (módulos jurídico/comunicação, gestão por equipe) voltam quando houver módulos que os justifiquem — não como filtro de visibilidade genérico.

---

## 2. Princípios gerais

1. **Need-to-know.** Visibilidade é a exceção concedida, não o default. A regra de demanda é por **envolvimento** (ver §3.3); pessoas/entidades só aparecem **no contexto de uma demanda** que o usuário pode ver.

2. **Dado de parte é vinculado ao contexto.** A ficha de uma pessoa/entidade (contato, endereço, vínculos) só é acessível a CG e Assessor **enquanto operam uma demanda ativa** ligada a ela. Fora disso, não há navegação pela base. Só o Admin navega o acervo.

3. **Exportar é exclusivo do Admin.** Nenhum botão de exportação (CSV) aparece para CG ou Assessor, em nenhuma lista. (Quem vê uma tela fotografa uma tela — mas o risco sistêmico de exfiltração da base é o que se elimina.) Cada export do Admin é registrado em auditoria (ADR 0053).

4. **`/auditoria`, `/analise` e Configurações são exclusivos do Admin.** Governança e visão agregada ficam numa única pessoa responsável.

5. **O flag `restrito` foi removido (ADR 0059, supersede ADR 0007).** No modelo need-to-know ele perdeu função — o Assessor já só vê as suas, o CG vê todas as ativas e o Admin vê tudo. Não há mais demanda "sigilosa" como exceção: a visibilidade é **inteiramente por papel**.

6. **Soft delete > hard delete.** Só o Admin exclui definitivamente. Desativar (soft delete) é ação de gestão (Admin/CG). Assessor não exclui nem desativa.

7. **Auditoria é universal no registro.** Toda criação/edição/exclusão em entidades críticas é logada (`django-auditlog`) — independentemente de quem pode *ler* o log.

---

## 3. Matriz por entidade

Colunas: **ADM** (Administrador), **CG** (Chefe de Gabinete), **AS** (Assessor).

### 3.1 Pessoas

| Ação | ADM | CG | AS |
|---|---|---|---|
| Listar / navegar a base (`/pessoas/`) | ✅ | ❌ | ❌ |
| Ver ficha completa (contato, endereço, vínculos) | ✅ | ✅ só no contexto de demanda ativa | ✅ só no contexto de demanda ativa dele |
| **Busca cega** (verificar existência ao cadastrar) | ✅ | ✅ | ✅ |
| Criar (cadastro mínimo ao abrir demanda) | ✅ | ✅ | ✅ |
| Editar | ✅ | ✅ (no contexto) | ✅ (no contexto) |
| Desativar / Reativar | ✅ | ✅ | ❌ |
| Excluir definitivamente · Anonimizar (LGPD) | ✅ | ❌ | ❌ |
| Exportar lista | ✅ | ❌ | ❌ |

### 3.2 Entidades

Igual a Pessoas (§3.1): lista/navegação e export só ADM; ficha só no contexto de demanda visível; busca cega para cadastrar.

### 3.3 Demandas — o núcleo do need-to-know

**Regra de visibilidade do Assessor:** vê uma demanda se é **responsável OU autor** dela.
- **Ativas** (status ≠ concluída/arquivada): contexto completo — incluindo os dados das partes daquela demanda.
- **Histórico próprio** (concluídas/arquivadas que ele tocou): **somente leitura**, com as partes **mascaradas** — o **nome** da parte aparece, mas **sem link para a ficha e sem dados de contato**.

**Chefe de Gabinete:** vê **todas as demandas ativas** (visão de gestão), com os dados das partes no contexto. **Não** vê o histórico concluído/arquivado.

**Admin:** vê todas, ativas e históricas.

| Ação | ADM | CG | AS |
|---|---|---|---|
| Listar demandas ativas | ✅ todas | ✅ todas | ✅ só as dele (responsável/autor) |
| Listar/ver demandas concluídas/arquivadas | ✅ todas | ❌ | ✅ só as próprias (leitura, partes mascaradas) |
| Criar demanda | ✅ | ✅ | ✅ |
| Editar demanda atribuída a si | ✅ | ✅ | ✅ |
| Editar demanda de outro | ✅ | ✅ (ativas) | ❌ |
| Atribuir/reatribuir responsável | ✅ | ✅ | ❌ |
| Atualizar `resultado` / concluir (com devolutiva) | ✅ | ✅ | ✅ (nas dele) |
| Arquivar | ✅ | ✅ | ❌ |
| Excluir definitivamente | ✅ | ❌ | ❌ |
| Exportar lista | ✅ | ❌ | ❌ |

### 3.4 Interações, 3.5 Encaminhamentos, 3.6 Anexos

Todos **herdam a visibilidade da demanda** à qual pertencem. Se o usuário pode ver/editar a demanda, pode ver/agir nas interações, encaminhamentos e anexos dela; senão, não.
- A lista transversal `/encaminhamentos/` aplica a mesma regra de demandas: Assessor vê só os das suas; CG os das ativas; Admin todos.
- Edição de interação própria em 24h; automáticas imutáveis (regra no model, inalterada).
- Excluir encaminhamento / anexo alheio: Admin (e CG nas ativas). Assessor não exclui.
- Exportar `/encaminhamentos/`: só Admin.

### 3.7 Tags e Temas (configuração)

| Ação | ADM | CG | AS |
|---|---|---|---|
| Atribuir tag/tema a registro | ✅ | ✅ | ✅ (no contexto) |
| Criar / editar / arquivar tag ou tema | ✅ | ❌ | ❌ |

### 3.8 Inbox

| Ação | ADM | CG | AS |
|---|---|---|---|
| Capturar (Ctrl+K, FAB, página) | ✅ | ✅ | ✅ |
| Listar / processar / descartar os **próprios** itens | ✅ | ✅ | ✅ |
| Ver itens de outros | ✅ | ❌ | ❌ |

### 3.9 Usuários · Configurações · Auditoria · Análise

| Ação | ADM | CG | AS |
|---|---|---|---|
| Gerir usuários (criar/editar/desativar) | ✅ | ❌ | ❌ |
| Editar próprio perfil / trocar senha | ✅ | ✅ | ✅ |
| Configurações (tags, temas, usuários) | ✅ | ❌ | ❌ |
| `/auditoria` | ✅ | ❌ | ❌ |
| `/analise` (métricas agregadas) | ✅ | ❌ | ❌ |

---

## 4. Busca cega (cadastro sem navegar a base)

Para CG e Assessor cadastrarem/vincularem uma pessoa numa demanda **sem** poder navegar o acervo:

1. O usuário digita telefone / CPF / nome.
2. O sistema responde apenas: **"já existe um registro compatível — vincular?"** — sem exibir a ficha, sem listar, sem permitir navegação.
3. Se existe, ele **vincula sem ver**. A ficha completa só aparece depois, no contexto da demanda ativa.
4. Se não existe, ele cria com **cadastro mínimo**.

Preserva a deduplicação (ponto forte do MPD) sem expor a base. Substitui, para não-Admin, o autocomplete atual que exibe a ficha.

---

## 5. Implementação técnica

Três camadas (defesa em profundidade) — falhar em uma não compromete a segurança:

1. **Template:** botões/links que o papel não pode usar não aparecem (export, `/analise`, `/auditoria`, listas de pessoas/entidades para não-Admin).
2. **View:** `PermissionRequiredMixin` / `UserPassesTestMixin` + helpers de `core/permissoes.py` (`eh_admin`, `eh_cg_plus`, …) — **única** fonte de checagem de papel (ADR 0024/0048).
3. **Model/QuerySet:** `Demanda.objects.visiveis_para(user)` (+ predicado Q reutilizável) centraliza a regra de visibilidade — vale para ORM, Admin, shell e API futura. Estendido na ADR 0059 para os 3 papéis e para o histórico-próprio-mascarado do Assessor.

O **mascaramento** de partes no histórico do Assessor é responsabilidade da camada de apresentação (nome sim; ficha/contato não) sobre demandas que o manager já liberou como "próprias concluídas".

---

## 6. Continuidade (risco do modelo)

Concentrar a visão total no Admin cria dependência de um único login. Por isso, são **críticos** (Fase 7):
- **Backup testado** (restore verificado), com dados no Brasil (LGPD).
- **Procedimento de recuperação da conta Admin** documentado.

---

## 7. Edge cases

- **Demanda anônima** (`anonimo=True`): segue a regra normal de visibilidade da demanda; não há parte para mascarar.
- **Pessoa anonimizada (LGPD)**: aparece como "[Pessoa removida]" onde quer que seja referenciada.
- **Responsável desativado**: a demanda continua existindo; aparece para o Admin/CG para reatribuição.
- **Assessor promovido/rebaixado**: muda de grupo; as demandas já atribuídas permanecem; a lista passa a refletir o novo papel.

---

## 8. Visibilidade pública

Sem login: `/healthz` (status, não-listado) e, na Fase 8, as rotas de privacidade/LGPD. Todo o resto redireciona para `/entrar?next=<url>`.

---

*Versão 2 (need-to-know) — ADR 0059, 2026-06-22. Supersede a v1 (colaborativo por default). Atualizar quando as regras mudarem (nova ADR).*
