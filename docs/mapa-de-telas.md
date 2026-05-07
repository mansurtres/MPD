# MPD — Mapa de Telas do MVP

Todas as rotas do sistema na `v1.0`. Para cada tela: rota, perfis com acesso, função, ações principais, fase de implementação.

> **Perfis:** `ADM` = Administrador, `CG` = Chefe de Gabinete, `CO` = Coordenador (Jurídico ou Comunicação), `AS` = Assessor.

---

## 1. Páginas Públicas (sem login)

### 1.1 Política de Privacidade
- **Rota:** `/privacidade`
- **Perfis:** público
- **Fase:** 5
- **Função:** aviso de privacidade do gabinete (LGPD).

### 1.2 Solicitação LGPD
- **Rota:** `/privacidade/solicitar`
- **Perfis:** público (rate limiting)
- **Fase:** 5
- **Função:** cidadão solicita acesso, correção, exclusão, portabilidade ou revogação.

---

## 2. Autenticação

### 2.1 Login
- **Rota:** `/entrar`
- **Perfis:** público
- **Fase:** 1

### 2.2 Recuperação de Senha
- **Rotas:** `/entrar/recuperar`, `/entrar/redefinir/<token>`
- **Perfis:** público
- **Fase:** 1

### 2.3 Logout
- **Rota:** `/sair`
- **Perfis:** todos logados
- **Fase:** 1

---

## 3. Início (Dashboard)

### 3.1 Início
- **Rota:** `/`
- **Perfis:** todos logados (conteúdo varia por perfil)
- **Fase:** 1 (esqueleto) → enriquecido nas fases seguintes
- **Função:** ponto de partida diário com o que importa para cada perfil.
- **Componentes por perfil:**
  - **ADM, CG:** total de casos abertos por coordenação, sem retorno há +30 dias, vencidos, pendentes no inbox, **carga por assessor** (top 5 com mais casos abertos), atividades recentes.
  - **CO:** casos da própria coordenação, prazos próximos, encaminhamentos aguardando retorno, **carga dos assessores da coordenação**.
  - **AS:** "Meus casos" priorizados, "Minhas interações pendentes" (agendadas vencidas e do dia), pendentes do inbox.
- **Ações:** captura rápida (Ctrl+K), criar caso, busca global.

---

## 4. Captura Rápida

### 4.1 Modal de Captura
- **Rota:** N/A (modal acionado por `Ctrl+K` ou botão flutuante)
- **Perfis:** todos logados
- **Fase:** 4
- **Função:** registrar item no inbox em segundos.
- **Comportamento:** `Enter` envia, `Shift+Enter` quebra linha, `Esc` fecha. HTMX, sem reload. Confirmação visual de 1s.

---

## 5. Inbox

### 5.1 Lista de Itens
- **Rota:** `/inbox`
- **Perfis:** todos logados
- **Fase:** 4
- **Função:** listar itens capturados, filtráveis por status.
- **Indicadores:** badge laranja em pendentes há +7 dias, vermelho em +30 dias.

### 5.2 Processar Item
- **Rota:** `/inbox/<id>/processar`
- **Perfis:** todos logados
- **Fase:** 4
- **Função:** transformar item bruto em caso estruturado.

### 5.3 Detalhe de Item Processado
- **Rota:** `/inbox/<id>`
- **Perfis:** todos logados
- **Fase:** 4

---

## 6. Cidadãos

### 6.1 Lista
- **Rota:** `/cidadaos`
- **Perfis:** todos logados
- **Fase:** 2 → 5 (filtros avançados, exportação)
- **Componentes:** tabela paginada (25/pg), busca, filtros (bairro, cidade, tag, período de cadastro).

### 6.2 Detalhe
- **Rota:** `/cidadaos/<id>`
- **Perfis:** todos logados (respeitando casos restritos)
- **Fase:** 2 (básico) → 3 (lista de casos)
- **Função:** ficha completa com toda a história relacional.
- **Componentes:** dados pessoais, endereço, communication preferences, vínculos com entidades, lista de casos cronológica reversa, histórico de alterações.

### 6.3 Novo / Editar
- **Rota:** `/cidadaos/novo`, `/cidadaos/<id>/editar`
- **Perfis:** AS, CO, CG, ADM
- **Fase:** 2
- **Validações:** pelo menos um entre email/telefone/whatsapp; bairro/cidade obrigatórios; CPF válido por algoritmo.

### 6.4 Anonimizar (LGPD)
- **Perfis:** CO, CG, ADM
- **Fase:** 5

---

## 7. Entidades

### 7.1 Lista
- **Rota:** `/entidades`
- **Fase:** 2 → 5

### 7.2 Detalhe
- **Rota:** `/entidades/<id>`
- **Fase:** 2 → 3

### 7.3 Nova / Editar
- **Rota:** `/entidades/nova`, `/entidades/<id>/editar`
- **Perfis:** AS, CO, CG, ADM
- **Fase:** 2

---

## 8. Casos

### 8.1 Lista
- **Rota:** `/casos`
- **Perfis:** todos logados (respeitando `restrito`)
- **Fase:** 3 → 5
- **Função:** listar casos com filtros poderosos.
- **Quick filters:** "Meus casos", "Da minha coordenação", "Vencidos", "Sem retorno há +30 dias", "Atendidos", "Não atendidos", "Sem resultado classificado".
- **Filtros avançados (Fase 5):** filtro por `resultado` (multi-select).

### 8.2 Detalhe
- **Rota:** `/casos/<id>`
- **Perfis:** conforme `restrito`
- **Fase:** 3
- **Função:** painel central de trabalho sobre um caso.
- **Componentes:**
  - Cabeçalho: número, título, status, prioridade, prazo, responsável, badges de tags, **badge de resultado** (com cor própria por valor).
  - Painel principal: descrição + timeline de interações (manuais e automáticas, distinguidas visualmente) em ordem cronológica.
  - Painel lateral: cidadão/entidade vinculados, encaminhamentos, anexos.
  - **Bloco de Resultado:** seletor de `resultado` + campo `resultado_observacao`. Editável a qualquer momento por quem pode editar o caso. Mudança gera interação automática `mudanca_resultado`.
  - Bloco de retorno (destaque visual quando preenchido).

### 8.3 Novo / Editar
- **Rota:** `/casos/novo`, `/casos/<id>/editar`
- **Perfis:** AS, CO, CG, ADM
- **Fase:** 3

### 8.4 Adicionar Interação
- **Modal/inline no detalhe**
- **Fase:** 3
- **Componentes:** tipo, conteúdo, **status (`realizada` ou `agendada`)**, data/hora.
- **Schedule Follow-up:** ao salvar como `realizada`, oferecer (checkbox) criar interação de follow-up: tipo, data futura, conteúdo. Cria nova interação com `status='agendada'` e `interacao_origem_id` apontando para esta.

### 8.5 Adicionar Encaminhamento
- **Fase:** 3

### 8.6 Registrar Resposta de Encaminhamento
- **Fase:** 3

### 8.7 Anexar Arquivo
- **Fase:** 3

### 8.8 Marcar como Respondido
- **Modal específico**
- **Fase:** 3
- **Bloqueio:** salva apenas se: (a) `retorno_data` e `retorno_conteudo` preenchidos; (b) `resultado` classificado (≠ `pendente`). Modal pré-popula `resultado` se já estiver preenchido no caso; senão exige escolha.

### 8.9 Arquivar
- **Perfis:** CO, CG, ADM
- **Fase:** 3

---

## 9. Interações Pessoais

### 9.1 Minhas Interações Pendentes
- **Rota:** `/minhas-pendencias`
- **Perfis:** todos logados
- **Fase:** 4
- **Função:** consolidar todas as interações onde o usuário é autor com `status='agendada'`.
- **Componentes:** tabela ordenada por `data_ocorrencia` (vencidas no topo, em vermelho), agrupadas por dia (Hoje / Amanhã / Esta semana / Próximas).
- **Ações:** marcar como realizada (com confirmação), cancelar, abrir caso correspondente.

### 9.2 Próximas Reuniões
- **Rota:** `/minhas-reunioes`
- **Perfis:** todos logados
- **Fase:** 4
- **Função:** view filtrada de Interações Pendentes, apenas tipo `reuniao`.
- **Componentes:** agenda visual simples (lista por dia, próximos 30 dias).

---

## 10. Análise

### 10.1 Painel
- **Rota:** `/analise`
- **Perfis:** CO, CG, ADM
- **Fase:** 5
- **Componentes:**
  - Cidadãos por bairro.
  - Casos por tema.
  - Casos por mês (série temporal textual).
  - Top 50 cidadãos com mais casos.
  - Encaminhamentos pendentes por órgão.
  - **Carga por assessor** (casos abertos, vencidos, tempo médio de resposta).
  - **Efetividade do mandato** (distribuição de `resultado` no período: % atendido, % parcial, % não atendido, % inviável, % não se aplica).
  - **Efetividade por tema** (resultado cruzado com tag de categoria `tema`).
  - **Efetividade por bairro** (resultado cruzado com bairro do cidadão).
  - **Efetividade por coordenação** (resultado cruzado com `coordenacao_responsavel`).
  - **Cidadãos com casos atendidos** (lista de cidadãos com pelo menos um caso `atendido` ou `atendido_parcialmente` no período — ordenável por quantidade).
  - **Casos resolvidos não comunicados** (lista operacional: `resultado` ≠ `pendente` E `status` ≠ `respondido` — pendentes de comunicar boa/má notícia ao cidadão).

---

## 11. Auditoria

### 11.1 Log
- **Rota:** `/auditoria`
- **Perfis:** CG, ADM
- **Fase:** 5
- **Implementação:** view consome tabela `auditlog_logentry`.

---

## 12. Configurações

### 12.1 Geral
- **Rota:** `/configuracoes`
- **Perfis:** ADM
- **Fase:** 1 → enriquecida

### 12.2 Usuários
- **Rota:** `/configuracoes/usuarios`
- **Perfis:** ADM
- **Fase:** 1

### 12.3 Novo / Editar Usuário
- **Rota:** `/configuracoes/usuarios/novo`, `/configuracoes/usuarios/<id>/editar`
- **Perfis:** ADM
- **Fase:** 1

### 12.4 Tags
- **Rota:** `/configuracoes/tags`
- **Perfis:** CO, CG, ADM
- **Fase:** 2 → 5 (mesclagem)

### 12.5 Solicitações LGPD
- **Rota:** `/configuracoes/lgpd`
- **Perfis:** CO, CG, ADM
- **Fase:** 5

---

## 13. Perfil Pessoal

### 13.1 Meu Perfil
- **Rota:** `/perfil`
- **Perfis:** todos logados
- **Fase:** 1

### 13.2 Trocar Senha
- **Rota:** `/perfil/senha`
- **Fase:** 1

---

## 14. Sistema

### 14.1 Health Check
- **Rota:** `/healthz`
- **Perfis:** público
- **Fase:** 5

### 14.2 Django Admin
- **Rota:** `/admin/`
- **Perfis:** ADM
- **Fase:** 0

---

## 15. Sumário por Fase

### Fase 0 (v0.1)
- 3.1 Início (versão "em construção")
- 14.2 Django Admin

### Fase 1 (v0.2)
- 2.1, 2.2, 2.3 Autenticação
- 3.1 Início (esqueleto por perfil)
- 12.1, 12.2, 12.3 Configurações + Usuários
- 13.1, 13.2 Perfil

### Fase 2 (v0.3)
- 6.1, 6.2 (sem casos), 6.3 Cidadãos
- 7.1, 7.2 (sem casos), 7.3 Entidades
- 12.4 Tags

### Fase 3 (v0.4)
- 6.2, 7.2 (com lista de casos)
- 8.1 a 8.9 Casos completos (incluindo Schedule Follow-up em 8.4)

### Fase 4 (v0.5)
- 4.1 Captura Rápida
- 5.1, 5.2, 5.3 Inbox
- 9.1, 9.2 Minhas Pendências e Próximas Reuniões

### Fase 5 (v0.6)
- 1.1, 1.2 LGPD público
- 6.1, 7.1, 8.1 (filtros avançados, exportação)
- 6.4 Anonimizar
- 10.1 Análise (com carga por assessor)
- 11.1 Auditoria
- 12.5 Solicitações LGPD
- 14.1 Health Check

### Fase 6 (v1.0)
- Polimento, mobile, manual, deploy. Sem novas telas.

---

## 16. Componentes transversais

**Layout:** topbar (logo, busca global, captura rápida, badge inbox, badge "minhas pendências vencidas", avatar), sidebar.

**UI:** tabela paginada (cards em mobile), filtros laterais, modal de confirmação, toast, empty state, autocomplete, badge de tag colorido, **timeline com distinção visual entre interações manuais e automáticas**, upload drag-and-drop, diff visual.

**Estados:** loading skeleton, empty state, error state, 403, 404.

---

## 17. Convenções de URL

- Coleções no plural: `/cidadaos`, `/casos`, `/entidades`.
- Detalhe sob a coleção: `/cidadaos/<id>`.
- Ações em português: `/casos/novo`, `/casos/<id>/editar`.
- Configurações sob `/configuracoes/`.
- Sistema sob raiz dedicada (`/healthz`, `/admin/`).
- Públicas em raiz, sem prefixo de autenticação.

---

## 18. Responsividade

Três breakpoints:
- **Mobile** (< 640px): sidebar em drawer, tabelas viram cards, formulários em coluna única, FAB para captura.
- **Tablet** (640–1024px): sidebar colapsável.
- **Desktop** (> 1024px): layout completo.

Verificação manual em Chrome desktop, Chrome Android, Safari iOS, Firefox.

---

*Atualizado a cada nova rota. Versão atual: planejamento, pré-Fase 0.*
