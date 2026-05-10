# MPD — Matriz de Permissões

Documento consolidado das regras de acesso e permissão do sistema. Define quem pode ver, criar, editar e excluir cada entidade.

> **Princípio:** o sistema é colaborativo, não compartimentalizado. O default é dar acesso. Restrições existem para demandas sensíveis específicas, não como regra geral.

> **Sobre este documento:** define a **configuração padrão** dos grupos criados na Fase 1 via data migration. O sistema usa Django Groups + Permissions nativos — o ADM pode criar novos grupos e ajustar permissões sem alterar código. Esta matriz não é regra hardcoded; é o ponto de partida. Ver ADR 0022.

---

## 1. Perfis

Quatro perfis, atribuídos via Django Group. Cada usuário pertence a exatamente um.

| Perfil | Quem é | Quantidade típica |
|---|---|---|
| **Administrador** (`ADM`) | Pedro (vereador, dono do sistema) | 1 |
| **Chefe de Gabinete** (`CG`) | Coordenação política geral do mandato | 1 |
| **Coordenador** (`CO`) | Coord. Jurídico ou Coord. de Comunicação | 2 |
| **Assessor** (`AS`) | Demais assessores parlamentares | 4-10 |

**Sub-tipos de Coordenador:** o sistema não tem grupos separados para Coord Jurídico vs Coord Comunicação. A distinção aparece pelo campo `coordenacao_responsavel` que cada um assume nas demandas. Um Coordenador Jurídico é simplesmente um usuário com perfil `CO` que predominantemente opera demandas com `coordenacao_responsavel='juridico'`. Isso evita inflar grupos sem necessidade — se mudar o coordenador, basta reatribuir as demandas.

---

## 2. Princípios gerais

**Default: visibilidade total entre perfis logados.** Demandas, pessoas, entidades, interações e encaminhamentos são visíveis a todos os usuários autenticados, exceto quando explicitamente restritos.

**Restrição é exceção, marcada explicitamente.** O campo `restrito` em `Demanda` é boolean único. Quando `TRUE`, a demanda é visível apenas para: responsável atribuído, Chefe de Gabinete e Administrador.

**Soft delete > hard delete.** Apenas Administrador pode excluir definitivamente. Coordenadores podem desativar (soft delete via `ativo=FALSE`). Assessores não excluem nem desativam.

**Auditoria é universal.** Toda criação, edição e exclusão em entidades críticas é registrada via `django-auditlog`. Ninguém escapa do log.

---

## 3. Matriz por entidade

### 3.1 Pessoas

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Listar | ✅ | ✅ | ✅ | ✅ |
| Ver detalhe | ✅ | ✅ | ✅ | ✅ |
| Criar | ✅ | ✅ | ✅ | ✅ |
| Editar | ✅ | ✅ | ✅ | ✅ |
| Desativar (soft delete) | ✅ | ✅ | ✅ | ❌ |
| Reativar desativada | ✅ | ✅ | ❌ | ❌ |
| Excluir definitivamente | ✅ | ❌ | ❌ | ❌ |
| Anonimizar (LGPD) | ✅ | ✅ | ✅ | ❌ |
| Adicionar tag | ✅ | ✅ | ✅ | ✅ |
| Adicionar vínculo com entidade | ✅ | ✅ | ✅ | ✅ |
| Exportar lista para CSV | ✅ | ✅ | ✅ | ❌ |
| Fazer upload de anexo | ✅ | ✅ | ✅ | ✅ |
| Excluir anexo | ✅ | ✅ | ✅ (próprios) | ❌ |

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
| Fazer upload de anexo | ✅ | ✅ | ✅ | ✅ |
| Excluir anexo | ✅ | ✅ | ✅ (próprios) | ❌ |

### 3.3 Demandas

Permissões com nuances. A coordenação importa.

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Listar demandas não-restritas | ✅ | ✅ | ✅ | ✅ (próprias + da coord) |
| Listar demandas restritas | ✅ | ✅ | ❌ | ✅ se for o responsável |
| Ver detalhe não-restrito | ✅ | ✅ | ✅ | ✅ |
| Ver detalhe restrito | ✅ | ✅ | ❌ | ✅ se for o responsável |
| Criar demanda | ✅ | ✅ | ✅ (própria coord) | ✅ |
| Editar demanda atribuída a si | ✅ | ✅ | ✅ | ✅ |
| Editar demanda atribuída a outro | ✅ | ✅ | ✅ (própria coord) | ❌ |
| Vincular / desvincular partes (pessoas e entidades) | ✅ | ✅ | ✅ (própria coord) | ✅ (atribuídas) |
| Atribuir/reatribuir responsável | ✅ | ✅ | ✅ (própria coord) | ❌ |
| Mudar coordenação responsável | ✅ | ✅ | ❌ | ❌ |
| Atualizar `resultado` da demanda | ✅ | ✅ | ✅ | ✅ (atribuídas) |
| Marcar como respondida | ✅ | ✅ | ✅ | ✅ (atribuídas) |
| Arquivar demanda respondida | ✅ | ✅ | ✅ | ❌ |
| Arquivar demanda não-respondida (com justificativa) | ✅ | ✅ | ❌ | ❌ |
| Marcar/desmarcar como restrita | ✅ | ✅ | ❌ | ❌ |
| Excluir demanda definitivamente | ✅ | ❌ | ❌ | ❌ |
| Exportar lista | ✅ | ✅ | ✅ | ❌ |

**Regra "AS de outra coordenação":** um Assessor da Comunicação não vê demandas da Jurídica (e vice-versa) por padrão, exceto se atribuído pessoalmente a ele. Isso reduz ruído na lista "minhas demandas" e respeita a divisão funcional.

### 3.4 Interações

A interação herda a permissão da demanda à qual pertence. Se o usuário pode ver a demanda, pode ver as interações.

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Ver timeline da demanda | ✅ | ✅ | ✅ | ✅ (se pode ver demanda) |
| Adicionar interação manual | ✅ | ✅ | ✅ | ✅ (se pode editar demanda) |
| Editar interação **própria** dentro de 24h | ✅ | ✅ | ✅ | ✅ |
| Editar interação alheia | ✅ | ✅ | ❌ | ❌ |
| Cancelar interação agendada própria | ✅ | ✅ | ✅ | ✅ |
| Cancelar interação agendada alheia | ✅ | ✅ | ✅ (própria coord) | ❌ |
| Marcar agendada como realizada | ✅ | ✅ | ✅ | ✅ (se for autor) |

**Janela de edição de 24h:** após criada, uma interação `realizada` pode ser editada pelo autor por 24h (correção de erros de digitação). Depois disso, fica imutável (apenas ADM/CG podem editar). Esta regra é codificada no model.

**Interações automáticas** (geradas por mudanças na demanda): nunca são editáveis por ninguém. São registros do sistema.

### 3.5 Encaminhamentos

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Ver | ✅ | ✅ | ✅ | ✅ (se pode ver demanda) |
| Criar | ✅ | ✅ | ✅ | ✅ (em demandas atribuídas) |
| Editar | ✅ | ✅ | ✅ | ✅ (em demandas atribuídas) |
| Registrar resposta | ✅ | ✅ | ✅ | ✅ (em demandas atribuídas) |
| Excluir | ✅ | ✅ | ❌ | ❌ |

### 3.6 Anexos

Permissão de visualização segue a entidade à qual o anexo pertence (demanda, pessoa, entidade ou encaminhamento). Upload segue a permissão de edição da entidade.

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Visualizar | ✅ | ✅ | ✅ | ✅ (se pode ver o objeto pai) |
| Upload em demanda | ✅ | ✅ | ✅ | ✅ (em demandas atribuídas) |
| Upload em pessoa / entidade | ✅ | ✅ | ✅ | ✅ |
| Upload em encaminhamento | ✅ | ✅ | ✅ | ✅ (em demandas atribuídas) |
| Editar descrição | ✅ | ✅ | ✅ | ✅ (próprios) |
| Excluir | ✅ | ✅ | ✅ (próprios ou da coord) | ❌ |

### 3.7 Tags

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Listar | ✅ | ✅ | ✅ | ✅ |
| Atribuir tag a pessoa/entidade/demanda | ✅ | ✅ | ✅ | ✅ |
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
| Processar item (converter em demanda) | ✅ | ✅ | ✅ | ✅ |
| Descartar item | ✅ | ✅ | ✅ | ✅ (próprios) |

### 3.9 Solicitações LGPD

| Ação | ADM | CG | CO | AS |
|---|---|---|---|---|
| Submeter (público, sem login) | — | — | — | — |
| Listar solicitações | ✅ | ✅ | ✅ | ❌ |
| Tratar (responder, atender, negar) | ✅ | ✅ | ✅ | ❌ |
| Gerar relatório PDF de pessoa | ✅ | ✅ | ✅ (Jurídico) | ❌ |

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
  - `pode_ver_demanda(user, demanda)` → considera `restrito`, `responsavel`, coordenação.
  - `pode_editar_demanda(user, demanda)` → considera atribuição e coordenação.

**No model:**

- `Demanda.objects.visiveis_para(user)` — manager method que retorna QuerySet filtrado conforme as regras de visibilidade do user.
- `Pessoa.objects.ativas()` — filtra por `ativo=True`.

**Em templates:**

- `{% if user|tem_grupo:'Administrador' %}` (template tag customizado).
- Botões de ação só aparecem se a permissão existe; clicar mesmo assim resulta em 403 server-side (defesa em profundidade).

---

## 5. Edge cases e regras especiais

### 5.1 Coordenador da própria coordenação

Quando se diz "Coord. Jurídico edita demandas da própria coordenação", a verificação é:

```python
def pode_editar_demanda(user, demanda):
    if user.groups.filter(name='Administrador').exists():
        return True
    if user.groups.filter(name='Chefe de Gabinete').exists():
        return True
    if user.groups.filter(name='Coordenador').exists():
        return _coordenacao_do_usuario(user) == demanda.coordenacao_responsavel
    if user.groups.filter(name='Assessor').exists():
        return demanda.responsavel_id == user.id
    return False
```

A função `_coordenacao_do_usuario(user)` infere a coordenação a partir do histórico. Em v1.x, isso pode virar campo explícito no perfil do usuário (`User.coordenacao`).

### 5.2 Demanda anônima (sem partes identificadas)

Demanda com `anonimo=TRUE` é visível por todos que poderiam ver demandas não-restritas. Não há regra adicional.

### 5.3 Demanda com múltiplas partes

Quando uma demanda tem várias pessoas e entidades vinculadas, as regras de visibilidade continuam se aplicando apenas sobre a demanda em si (via `restrito` e coordenação), não sobre as partes individualmente.

### 5.4 Pessoa anonimizada por LGPD

Pessoa com `anonimizado=TRUE` aparece em listagens com nome `"[Pessoa Removida]"`. Demandas vinculadas continuam visíveis (sem nome da pessoa), porque demandas têm valor histórico/estatístico próprio.

### 5.5 Usuário desativado

Usuário com `is_active=FALSE` não consegue logar. Suas atribuições anteriores em demandas permanecem (FK preservada). Demandas atribuídas a usuário desativado aparecem na lista como "responsável inativo" — sinal para reatribuir.

### 5.6 Perfis em transição

Quando um usuário muda de grupo (ex: Assessor é promovido a Coordenador), as demandas já atribuídas a ele permanecem. A nova lista "demandas da minha coordenação" passa a incluir mais demandas automaticamente.

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

Acessos a recursos individuais (visualização de pessoa, demanda, interação) **não são logados** por padrão — geraria volume gigante. Se necessário, ativável via configuração.

---

## 8. Princípio de defesa em profundidade

Todas as verificações de permissão são feitas em **três camadas**:

1. **Template:** botões e links que o usuário não pode usar não aparecem.
2. **View:** decorator/mixin verifica permissão antes de processar.
3. **Model/QuerySet:** managers customizados garantem que mesmo um acesso direto (Django Admin, shell, API futura) respeite as regras.

Falhar em qualquer camada não compromete a segurança — as outras seguram.

---

*Atualizado quando regras mudam. Versão atual: planejamento, pré-Fase 1.*
