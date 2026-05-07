# MPD — Matriz de Permissões

Documento consolidado das regras de acesso e permissão do sistema. Define quem pode ver, criar, editar e excluir cada entidade.

> **Princípio:** o sistema é colaborativo, não compartimentalizado. O default é dar acesso. Restrições existem para casos sensíveis específicos, não como regra geral.

---

## 1. Perfis

Quatro perfis, atribuídos via Django Group. Cada usuário pertence a exatamente um.

| Perfil | Quem é | Quantidade típica |
|---|---|---|
| **Administrador** (`ADM`) | Pedro (vereador, dono do sistema) | 1 |
| **Chefe de Gabinete** (`CG`) | Coordenação política geral do mandato | 1 |
| **Coordenador** (`CO`) | Coord. Jurídico ou Coord. de Comunicação | 2 |
| **Assessor** (`AS`) | Demais assessores parlamentares | 4-10 |

**Sub-tipos de Coordenador:** o sistema não tem grupos separados para Coord Jurídico vs Coord Comunicação. A distinção aparece pelo campo `coordenacao_responsavel` que cada um assume nos casos. Um Coordenador Jurídico é simplesmente um usuário com perfil `CO` que predominantemente opera casos com `coordenacao_responsavel='juridico'`. Isso evita inflar grupos sem necessidade — se mudar o coordenador, basta reatribuir os casos.

---

## 2. Princípios gerais

**Default: visibilidade total entre perfis logados.** Casos, cidadãos, entidades, interações e encaminhamentos são visíveis a todos os usuários autenticados, exceto quando explicitamente restritos.

**Restrição é exceção, marcada explicitamente.** O campo `restrito` em `Caso` é boolean único. Quando `TRUE`, o caso é visível apenas para: responsável atribuído, Chefe de Gabinete e Administrador.

**Soft delete > hard delete.** Apenas Administrador pode excluir definitivamente. Coordenadores podem desativar (soft delete via `ativo=FALSE`). Assessores não excluem nem desativam.

**Auditoria é universal.** Toda criação, edição e exclusão em entidades críticas é registrada via `django-auditlog`. Ninguém escapa do log.

---

## 3. Matriz por entidade

### 3.1 Cidadãos

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Listar (excluindo casos restritos cujo cidadão se vê só por isso) | ✅ | ✅ | ✅ | ✅ |
| Ver detalhe | ✅ | ✅ | ✅ | ✅ |
| Criar | ✅ | ✅ | ✅ | ✅ |
| Editar | ✅ | ✅ | ✅ | ✅ |
| Desativar (soft delete) | ✅ | ✅ | ✅ | ❌ |
| Reativar desativado | ✅ | ✅ | ❌ | ❌ |
| Excluir definitivamente | ✅ | ❌ | ❌ | ❌ |
| Anonimizar (LGPD) | ✅ | ✅ | ✅ | ❌ |
| Adicionar tag | ✅ | ✅ | ✅ | ✅ |
| Adicionar vínculo com entidade | ✅ | ✅ | ✅ | ✅ |
| Editar communication preferences | ✅ | ✅ | ✅ | ✅ |
| Exportar lista para CSV | ✅ | ✅ | ✅ | ❌ |

### 3.2 Entidades

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Listar | ✅ | ✅ | ✅ | ✅ |
| Ver detalhe | ✅ | ✅ | ✅ | ✅ |
| Criar | ✅ | ✅ | ✅ | ✅ |
| Editar | ✅ | ✅ | ✅ | ✅ |
| Desativar | ✅ | ✅ | ✅ | ❌ |
| Excluir definitivamente | ✅ | ❌ | ❌ | ❌ |
| Exportar | ✅ | ✅ | ✅ | ❌ |

### 3.3 Casos

Permissões com nuances. A coordenação importa.

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Listar casos não-restritos | ✅ | ✅ | ✅ | ✅ (próprios + da coord) |
| Listar casos restritos | ✅ | ✅ | ❌ | ✅ se for o responsável |
| Ver detalhe não-restrito | ✅ | ✅ | ✅ | ✅ |
| Ver detalhe restrito | ✅ | ✅ | ❌ | ✅ se for o responsável |
| Criar caso | ✅ | ✅ | ✅ (própria coord) | ✅ |
| Editar caso atribuído a si | ✅ | ✅ | ✅ | ✅ |
| Editar caso atribuído a outro | ✅ | ✅ | ✅ (própria coord) | ❌ |
| Atribuir/reatribuir responsável | ✅ | ✅ | ✅ (própria coord) | ❌ |
| Mudar coordenação responsável | ✅ | ✅ | ❌ | ❌ |
| Atualizar `resultado` do caso | ✅ | ✅ | ✅ | ✅ (atribuídos) |
| Marcar como respondido | ✅ | ✅ | ✅ | ✅ (atribuídos) |
| Arquivar caso respondido | ✅ | ✅ | ✅ | ❌ |
| Arquivar caso não-respondido (com justificativa) | ✅ | ✅ | ❌ | ❌ |
| Marcar/desmarcar como restrito | ✅ | ✅ | ❌ | ❌ |
| Excluir caso definitivamente | ✅ | ❌ | ❌ | ❌ |
| Exportar lista | ✅ | ✅ | ✅ | ❌ |

**Regra "AS de outra coordenação":** um Assessor da Comunicação não vê casos da Jurídica (e vice-versa) por padrão, exceto se atribuído pessoalmente a ele. Isso reduz ruído na lista "meus casos" e respeita a divisão funcional.

### 3.4 Interações

A interação herda a permissão do caso ao qual pertence. Se o usuário pode ver o caso, pode ver as interações.

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Ver timeline do caso | ✅ | ✅ | ✅ | ✅ (se pode ver caso) |
| Adicionar interação manual | ✅ | ✅ | ✅ | ✅ (se pode editar caso) |
| Editar interação **própria** dentro de 24h | ✅ | ✅ | ✅ | ✅ |
| Editar interação alheia | ✅ | ✅ | ❌ | ❌ |
| Cancelar interação agendada própria | ✅ | ✅ | ✅ | ✅ |
| Cancelar interação agendada alheia | ✅ | ✅ | ✅ (própria coord) | ❌ |
| Marcar agendada como realizada | ✅ | ✅ | ✅ | ✅ (se for autor) |

**Janela de edição de 24h:** após criada, uma interação `realizada` pode ser editada pelo autor por 24h (correção de erros de digitação). Depois disso, fica imutável (apenas ADM/CG podem editar). Esta regra é codificada no model.

**Interações automáticas** (geradas por mudanças no caso): nunca são editáveis por ninguém. São registros do sistema.

### 3.5 Encaminhamentos

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Ver | ✅ | ✅ | ✅ | ✅ (se pode ver caso) |
| Criar | ✅ | ✅ | ✅ | ✅ (em casos atribuídos) |
| Editar | ✅ | ✅ | ✅ | ✅ (em casos atribuídos) |
| Registrar resposta | ✅ | ✅ | ✅ | ✅ (em casos atribuídos) |
| Excluir | ✅ | ✅ | ❌ | ❌ |

### 3.6 Anexos

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Visualizar | ✅ | ✅ | ✅ | ✅ (se pode ver caso) |
| Upload | ✅ | ✅ | ✅ | ✅ (em casos atribuídos) |
| Editar descrição | ✅ | ✅ | ✅ | ✅ (em casos atribuídos) |
| Excluir | ✅ | ✅ | ✅ (em casos da coord) | ❌ |

### 3.7 Tags

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Listar | ✅ | ✅ | ✅ | ✅ |
| Atribuir tag a cidadão/entidade/caso | ✅ | ✅ | ✅ | ✅ |
| Criar nova tag | ✅ | ✅ | ✅ | ❌ |
| Editar tag (nome, cor, descrição) | ✅ | ✅ | ✅ | ❌ |
| Mesclar duas tags (v0.6) | ✅ | ✅ | ❌ | ❌ |
| Inativar tag | ✅ | ✅ | ❌ | ❌ |

### 3.8 Inbox

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Capturar item (Ctrl+K, FAB, página) | ✅ | ✅ | ✅ | ✅ |
| Listar pendentes | ✅ | ✅ | ✅ | ✅ |
| Listar processados/descartados | ✅ | ✅ | ✅ | ✅ (próprios) |
| Processar item (converter em caso) | ✅ | ✅ | ✅ | ✅ |
| Descartar item | ✅ | ✅ | ✅ | ✅ (próprios) |

### 3.9 Solicitações LGPD

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Submeter (público, sem login) | — | — | — | — |
| Listar solicitações | ✅ | ✅ | ✅ | ❌ |
| Tratar (responder, atender, negar) | ✅ | ✅ | ✅ | ❌ |
| Gerar relatório PDF de cidadão | ✅ | ✅ | ✅ (Jurídico) | ❌ |

### 3.10 Usuários

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Listar usuários | ✅ | ✅ | ❌ | ❌ |
| Criar usuário | ✅ | ❌ | ❌ | ❌ |
| Editar usuário (exceto próprio perfil/senha) | ✅ | ❌ | ❌ | ❌ |
| Desativar usuário | ✅ | ❌ | ❌ | ❌ |
| Forçar troca de senha | ✅ | ❌ | ❌ | ❌ |
| Editar próprio perfil | ✅ | ✅ | ✅ | ✅ |
| Trocar própria senha | ✅ | ✅ | ✅ | ✅ |

### 3.11 Configurações Gerais

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Ver configurações gerais | ✅ | ✅ | ❌ | ❌ |
| Editar configurações gerais | ✅ | ❌ | ❌ | ❌ |
| Acessar Django Admin | ✅ | ❌ | ❌ | ❌ |

### 3.12 Auditoria

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Ver log de auditoria | ✅ | ✅ | ❌ | ❌ |
| Exportar log | ✅ | ✅ | ❌ | ❌ |

---

## 4. Implementação técnica

**Decoradores e Mixins do Django:**

- `@login_required` em todas as views autenticadas.
- `@permission_required` ou `UserPassesTestMixin` para checagens de perfil.
- Helpers customizados em `core/permissions.py`:
  - `is_admin(user)` → True se grupo Administrador.
  - `is_cg_or_above(user)` → True se ADM ou CG.
  - `is_co_or_above(user)` → True se ADM, CG ou CO.
  - `pode_ver_caso(user, caso)` → considera `restrito`, `responsavel`, coordenação.
  - `pode_editar_caso(user, caso)` → considera atribuição e coordenação.

**No model:**

- `Caso.objects.visiveis_para(user)` — manager method que retorna QuerySet filtrado conforme as regras de visibilidade do user.
- `Cidadao.objects.ativos()` — filtra por `ativo=True`.

**Em templates:**

- `{% if user|tem_grupo:'Administrador' %}` (template tag customizado).
- Botões de ação só aparecem se a permissão existe; clicar mesmo assim resulta em 403 server-side (defesa em profundidade).

---

## 5. Edge cases e regras especiais

### 5.1 Coordenador da própria coordenação

Quando se diz "Coord. Jurídico edita casos da própria coordenação", a verificação é:

```python
def pode_editar_caso(user, caso):
    if user.groups.filter(name='Administrador').exists():
        return True
    if user.groups.filter(name='Chefe de Gabinete').exists():
        return True
    if user.groups.filter(name='Coordenador').exists():
        # Coordenador edita se o caso é da coordenação onde ele atua predominantemente
        # Determinada pela coordenacao_responsavel mais frequente em casos atribuídos a ele
        # OU configurada manualmente no perfil dele (futuro)
        return _coordenacao_do_usuario(user) == caso.coordenacao_responsavel
    if user.groups.filter(name='Assessor').exists():
        return caso.responsavel_id == user.id
    return False
```

A função `_coordenacao_do_usuario(user)` infere a coordenação a partir do histórico. Em v1.x, isso pode virar campo explícito no perfil do usuário (`User.coordenacao`).

### 5.2 Caso anônimo (sem cidadão titular)

Caso com `anonimo=TRUE` é visível por todos que poderiam ver casos não-restritos. Não há regra adicional.

### 5.3 Caso vinculado a Entidade (sem cidadão)

Mesma regra: visibilidade segue `restrito` e atribuição. Entidade não confere privacidade extra.

### 5.4 Cidadão anonimizado por LGPD

Cidadão com `anonimizado=TRUE` aparece em listagens com nome `"[Cidadão Removido]"`. Casos vinculados continuam visíveis (sem nome do cidadão), porque casos têm valor histórico/estatístico próprio.

### 5.5 Usuário desativado

Usuário com `is_active=FALSE` não consegue logar. Suas atribuições anteriores em casos permanecem (FK preservada). Casos atribuídos a usuário desativado aparecem na lista de casos como "responsável inativo" — sinal para reatribuir.

### 5.6 Perfis em transição

Quando um usuário muda de grupo (ex: Assessor é promovido a Coordenador), os casos já atribuídos a ele permanecem. A nova lista "casos da minha coordenação" passa a incluir mais casos automaticamente.

---

## 6. Visibilidade pública

Apenas duas rotas públicas (sem login):

- `/privacidade` — aviso de privacidade.
- `/privacidade/solicitar` — formulário de solicitação LGPD (com rate limiting via `django-ratelimit`).
- `/healthz` — JSON de status do sistema (não-listado).

Nenhuma outra rota é acessível sem autenticação. Tentativas redirecionam para `/entrar?next=<url>`.

---

## 7. Auditoria de acessos

Todos os logins, falhas de login e logouts são registrados em log dedicado (`django-axes` ou similar, configurado em Fase 5):

- Login bem-sucedido: usuário, IP, timestamp.
- Login falho: email tentado, IP, timestamp.
- Após 5 falhas em 10 minutos: rate limiting de 15 minutos para o IP.

Acessos a recursos individuais (visualização de cidadão, caso, interação) **não são logados** por padrão — geraria volume gigante. Se necessário, ativável via configuração.

---

## 8. Princípio de defesa em profundidade

Todas as verificações de permissão são feitas em **três camadas**:

1. **Template:** botões e links que o usuário não pode usar não aparecem.
2. **View:** decorator/mixin verifica permissão antes de processar.
3. **Model/QuerySet:** managers customizados garantem que mesmo um acesso direto (Django Admin, shell, API futura) respeite as regras.

Falhar em qualquer camada não compromete a segurança — as outras seguram.

---

*Atualizado quando regras mudam. Versão atual: planejamento, pré-Fase 0.*
