# Briefing — Protótipo de alta fidelidade do MPD

> Documento de entrega para a pessoa designer/dev front-end responsável pela prototipação.
> **Owner do produto:** Pedro Tres. **Tom técnico:** consultivo (Pedro é leigo em técnica).
> **Data:** 2026-05-18. **Versão do produto referenciada:** v0.7.3.

---

## 1. O que é o MPD

**Mandato Parlamentar Digital** é um sistema de gestão de relacionamento político (categoria *constituent management*) para um mandato municipal. É de **uso interno** pela equipe do gabinete — não há área pública para cidadão na v1.

A unidade central é a **Pessoa**. **Demandas** (pedidos, encaminhamentos, denúncias, sugestões) orbitam a pessoa. O sistema rastreia todo o ciclo de vida de uma demanda — da captura até a devolutiva ao demandante — passando por interações, encaminhamentos a órgãos externos, anexos, prazos e responsáveis.

Hoje o produto está em **v0.7.3** com 226 testes passando e backend pronto. A UI atual é funcional mas crua (Tailwind sem identidade). O objetivo deste protótipo é **redesenhar todas as telas com identidade, fluidez e qualidade visual de produto SaaS moderno**.

### Quem usa
4 perfis, em ordem de poder:
- **Administrador (ADM)** — dono do sistema, ajusta configurações, gerencia equipe.
- **Chefe de Gabinete (CG)** — visão geral, acesso à auditoria.
- **Coordenador (CO)** — responsável por uma coordenação (Jurídico, Comunicação etc.), gerencia equipe e demandas da própria área. Acessa painel de análise e exporta CSV.
- **Assessor (AS)** — atende demandas, registra interações, captura inbox. Não vê demandas marcadas como restritas fora da própria coordenação.

### Uso típico
- Equipe usa o sistema várias horas por dia.
- Telas de lista (demandas, pessoas, inbox, pendências) são escaneadas constantemente.
- Tela de detalhe da demanda é onde mora a maior parte do trabalho (timeline + ações).
- Inbox é alimentado o dia inteiro com itens capturados via Ctrl+K (durante visitas, ligações, conversas).

---

## 2. Objetivo do protótipo

Entregar **alta fidelidade** dos **8 padrões de tela** que cobrem as 36 rotas do sistema. O dev de back-end (Claude Code) traduzirá esses protótipos para Django templates + Tailwind v4.

**Não é** wireframe. **Não é** PoC. É a referência visual definitiva de como o produto se parece e se comporta.

### O conjunto de 8 protótipos cobre as 36 telas
Os formulários, listas e detalhes da maior parte do sistema são variações de padrões. Por isso 8 protótipos bem feitos resolvem o conjunto.

| # | Padrão | Tela canônica | Variações que cobre |
|---|---|---|---|
| 1 | Shell autenticado (topbar, busca global, badges, toast, modal Ctrl+K) | Aparece em todas | base de tudo |
| 2 | Login | `/entrar/` | shell público |
| 3 | Home + Hub de configurações | `/` e `/configuracoes/` | grids de cards |
| 4 | Lista rica (filtros + quick filters + colunas + ações em massa + export + paginação + vazio) | `/demandas/` | `/pessoas/`, `/entidades/`, `/encaminhamentos/`, `/inbox/`, `/auditoria/`, `/configuracoes/usuarios/`, `/configuracoes/tags/`, `/configuracoes/temas/` |
| 5 | Formulário complexo (formsets dinâmicos, autocomplete, upload, popup inline de criar) | `/demandas/nova/` | todos os `nova/` e `editar/` (~14 telas), incluindo `/inbox/<uuid>/processar/` |
| 6 | Detalhe rico (timeline + partes + encaminhamentos + anexos + CTA principal + drawer lateral + modais) | `/demandas/<uuid>/` | `/pessoas/<slug>/`, `/entidades/<slug>/` (versões reduzidas) |
| 7 | Pendências/Inbox (agrupamento temporal com badges de envelhecimento) | `/minhas-pendencias/` | `/minhas-reunioes/`, lista da `/inbox/` |
| 8 | Painel de análise (cards com toggle tabela/gráfico + filtros globais) | `/analise/` | referência para diff visual de `/auditoria/` |

A lista completa de rotas está em [`mapa-de-telas.md`](mapa-de-telas.md) (rotas formais) e na §7 deste documento (catálogo prático para o protótipo).

---

## 3. Decisões já tomadas

Travadas pelo product owner para evitar retrabalho:

| Decisão | Valor | Implicação |
|---|---|---|
| **Plataforma** | Desktop + mobile responsivo | Cada tela precisa ter versão mobile. Mobile ≠ "miniatura"; em campo, o assessor captura inbox, marca interação realizada, e visualiza demanda no celular. |
| **Densidade** | Confortável (mais respiro) | Padrão tipo Linear/Notion. Espaços generosos, tipografia legível, foco em redução de fadiga. **Não** é Airtable denso. |
| **Identidade visual** | Carta branca para o dev propor | Não há paleta nem fonte travadas. Propor 1 direção (com 2 cores principais, neutros, semânticas) e validar com Pedro antes de aplicar nos 8 protótipos. |
| **Tema escuro** | Bônus — não obrigatório no v1 | Se vier, ótimo. Não bloqueia entrega. |
| **Stack de pouso** | Django templates + Tailwind v4 (utility-first) + Chart.js v4 (gráficos) | Sem build de Node. O protótipo não precisa virar componentes React — só precisa ser traduzível para HTML + classes Tailwind. |

### Restrição de identidade
O mandato é **municipal e genérico** (sem nome travado). O protótipo deve usar um nome-placeholder como **"Gabinete Demo"** ou **"MPD — Mandato Demo"**. Não inventar nome real, partido, ou cidade.

---

## 4. Glossário de domínio (essencial para entender as telas)

| Termo | Definição |
|---|---|
| **Pessoa** | Cidadão registrado. Núcleo do sistema. Pode ter múltiplos telefones, e-mails e redes sociais. |
| **Entidade** | Organização (associação, escola, secretaria, família, grupo informal etc.). 14 tipos. Pode ter vínculos com pessoas. |
| **Vínculo** | Relação entre Pessoa e Entidade (presidente da associação X, mãe de aluno da escola Y). |
| **Tag** | Rótulo plano e colorido em Pessoa ou Entidade (sem categoria/hierarquia). 11 cores fixas. |
| **Demanda** | Solicitação ou ação registrada. Tem origem (responsiva = veio do cidadão; proativa = gabinete iniciou). Identificada por número `MPD-AAAA-NNNNN`. |
| **Status da demanda** | Eixo do ciclo de trabalho: `novo` → `em_andamento` → `aguardando_*` → `concluida` → `arquivada`. |
| **Resultado da demanda** | Eixo do desfecho material: `pendente`, `atendido`, `atendido_parcialmente`, `nao_atendido`, `inviavel`, `nao_se_aplica`. **Independente do status.** |
| **Devolutiva** | Retorno formal ao demandante. É uma **Interação** especial (tipo `devolutiva`). Responsiva só pode ser concluída com devolutiva registrada. |
| **Interação** | Evento na timeline da demanda: ligação, reunião, e-mail, recado, devolutiva. Pode ser **realizada** (passado, com data e conteúdo) ou **agendada** (futuro, vira pendência). |
| **Encaminhamento** | Documento formal enviado a órgão externo (ofício, requerimento, indicação etc.) cobrando providência. Tem prazo, status de resposta, e número de protocolo opcional. |
| **Anexo** | Arquivo (até 25 MB, mime whitelist) pendurado em Demanda, Pessoa, Entidade ou Encaminhamento. Polimórfico. |
| **Inbox / Item de Inbox** | Captura rápida ("anote para processar depois"). Item pode virar Demanda ou ser descartado com motivo. |
| **Coordenação** | Atributo do Usuário (Jurídico, Comunicação etc.). Determina visibilidade de demandas restritas. |
| **Demanda restrita** | Marcada como confidencial; só visível para autor, responsável, e usuários da mesma coordenação + CG/ADM. |
| **Tema** | Eixo temático da demanda (saúde, educação, infraestrutura etc.). Configurável pelo admin. |

### A regra de ouro do domínio
> Demanda responsiva só vai para `concluida` com **devolutiva registrada** (interação tipo `devolutiva`) **e** `resultado` classificado (não pode ser `pendente`).
> Demanda proativa pode ser concluída sem devolutiva — basta `resultado` classificado.

Isso afeta o CTA de "Concluir demanda" no detalhe (§7, padrão 6) — o botão se comporta diferente conforme a origem.

---

## 5. Perfis e permissões — como afetam a UI

Cada perfil enxerga subconjuntos diferentes da interface. O protótipo deve mostrar a UI **do perfil de Coordenador** como caso canônico (vê quase tudo, mas não tem auditoria). Variações:

| Item da UI | ADM | CG | CO | AS |
|---|---|---|---|---|
| Topbar: link "Auditoria" | ✅ | ✅ | — | — |
| Topbar: link "Painel de Análise" / Análise no hub | ✅ | ✅ | ✅ | — |
| Botão "Exportar CSV" nas listas | ✅ | ✅ | ✅ | — |
| Botão "Marcar demanda como restrita" | ✅ | ✅ | ✅ | — |
| Card "Usuários" em `/configuracoes/` | ✅ | — | — | — |
| Card "Tags" / "Temas" em `/configuracoes/` | ✅ | ✅ | ✅ | — |
| Ver demanda restrita de outra coordenação | ✅ | ✅ | — | — |

Para os 8 protótipos, mostrar a **versão Coordenador** + uma anotação onde houver elemento gated ("Visível apenas para ADM/CG"). Não é necessário desenhar todas as 4 variações de cada tela. A matriz completa está em [`permissoes.md`](permissoes.md).

---

## 6. Estados obrigatórios (todos os protótipos)

Para cada protótipo, mostrar pelo menos:
1. **Estado padrão** (preenchido com dados realistas — não Lorem ipsum)
2. **Estado vazio** (primeiro uso, sem registros, com CTA claro)
3. **Estado de erro** (validação de formulário, falha de upload, sessão expirada)
4. **Estado de loading** (skeleton para listas e detalhe; spinner para ações)
5. **Estado de sucesso** (toast após ação, confirmação visual)

Variações úteis a incluir:
- Hover, focus, disabled em botões e inputs.
- Demanda com timeline curta (1 evento) e timeline longa (8+ eventos).
- Lista com 1 item, com muitos itens (rolagem + paginação), e vazia.

---

## 7. Detalhamento dos 8 protótipos

### Protótipo 1 — Shell autenticado (frame de todas as telas internas)

**Componentes do shell:**
- **Topbar** fixa no topo. Esquerda: logomarca + nome "MPD". Centro: busca global (placeholder "Buscar pessoa, demanda, MPD-AAAA-NNNNN…"). Direita (nessa ordem): Inbox (com badge cinza com count de pendentes) · Pendências (com badge vermelho de vencidas) · Demandas · Pessoas · Entidades · Encaminhamentos · Análise · Auditoria · Configurações · avatar do usuário (dropdown com Perfil / Sair).
- **FAB** (botão flutuante) `+` no canto inferior direito, sempre visível. Abre o **modal de captura rápida** (Ctrl+K).
- **Modal Ctrl+K**: aparece centralizado, fundo escurecido. Textarea grande, dica "Enter envia, Shift+Enter quebra linha, Esc fecha". Após envio: confirmação "Capturado!" 800ms, fecha sozinho.
- **Toast** (canto inferior direito): aparece após ações (sucesso, erro, info). Auto-dismiss em 4s. Empilhável.
- **Breadcrumb** (opcional, no topo das telas internas): "Demandas › MPD-2026-00042".
- **Footer minimalista**: versão do sistema, link para suporte.

**Variação mobile:**
- Topbar vira hambúrguer + logo + ícones essenciais (busca, inbox, avatar).
- Menu lateral por drawer ao tocar no hambúrguer.
- FAB permanece.
- Modal Ctrl+K vira página cheia em mobile (não modal).

**Tokens a definir aqui:**
- Cores primárias (2), neutros (escala 50–950), semânticas (sucesso, aviso, perigo, info).
- **Cores de status de demanda**: `novo`, `em_andamento`, `aguardando_resposta`, `aguardando_terceiro`, `concluida`, `arquivada`. 6 cores distintas.
- **Cores de resultado**: `pendente` (neutro), `atendido` (verde), `atendido_parcialmente` (âmbar), `nao_atendido` (vermelho), `inviavel` (cinza-escuro), `nao_se_aplica` (cinza).
- Tipografia: família, escala (xs, sm, base, lg, xl, 2xl, 3xl).
- Espaçamento (escala Tailwind padrão geralmente serve).
- Sombra (3 níveis), raio (sm, md, lg, full).

---

### Protótipo 2 — Login

**Rota:** `/entrar/`

Tela única, shell público.

- Centralizada. Card com logomarca + título "Acesse o MPD".
- Campos: e-mail, senha, checkbox "Lembrar-me por 30 dias".
- Botão primário "Entrar".
- Link "Esqueci minha senha" (Fase 1, ainda não implementado — mostrar como link).
- **Estado de erro:** mensagem inline "E-mail ou senha incorretos. 3 tentativas restantes." (django-axes faz lockout após 5 falhas em 30min — desenhar também o estado bloqueado: "Conta temporariamente bloqueada. Tente novamente em X minutos.").

---

### Protótipo 3 — Home + Hub de configurações

**Rotas:** `/` (home autenticada), `/configuracoes/`

Padrão grid de cards.

**Home (`/`):**
- Saudação ("Boa tarde, Maria") com contexto do papel.
- **Métricas-resumo do dia** (cards pequenos): minhas pendências vencidas · novos itens no inbox · demandas atribuídas a mim.
- **Cards de ação rápida**: "Capturar no Inbox" (atalho Ctrl+K) · "Nova demanda" · "Buscar pessoa".
- **Mosaico de atalhos** (cards médios): Demandas, Pessoas, Entidades, Encaminhamentos, Inbox, Pendências, Análise, Configurações.
- Lista resumida das 5 demandas mais recentes na minha coordenação.

**Hub de configurações (`/configuracoes/`):**
- Grid de cards: Usuários (ADM) · Tags · Temas · Painel de Análise (CO+) · Auditoria (CG+) · Perfil.
- Cada card: ícone + título + descrição curta (1 linha).
- Cards gated aparecem desabilitados (cinza) ou somem para perfis sem acesso. **Decidir e mostrar uma das opções.**

---

### Protótipo 4 — Lista rica (canônica: `/demandas/`)

A tela mais usada. Modelo de referência para 8 listas do sistema.

**Header:**
- Título "Demandas" + contador ("142 demandas, 38 abertas").
- Botão primário "Nova demanda".
- Menu de ações: "Exportar CSV" (CO+).

**Filtros (linha sticky abaixo do header):**
- **Quick filters** (chips horizontais, multi-toggle): "Minhas" · "Da minha coordenação" · "Vencidas" · "Sem devolutiva +30d" · "Com encaminhamento aberto" · "Sem encaminhamento" · "Atendidas" · "Não atendidas" · "Sem resultado".
- **Filtros avançados** (botão "Filtros" abre painel lateral): status, resultado, responsável (autocomplete), tema (multi-select), origem, coordenação, período (data de criação), texto livre.
- Chips de filtros ativos aparecem abaixo, com X para remover individualmente. Botão "Limpar tudo".

**Tabela:**
- Colunas: Nº (MPD-AAAA-NNNNN, monospace) · Título · Status (badge colorido) · Resultado (badge colorido) · Responsável · Tema · Atualizada em.
- Linha clicável (vai para o detalhe). Hover destaca a linha.
- Ícones inline: 📎 se tem anexo, 📨 se tem encaminhamento aberto, 🔒 se restrita.
- Densidade: confortável, mas com line-height controlado para caber ~15 linhas em viewport 1080p.

**Paginação:**
- "25 por página", controles "Anterior · 1 2 3 … · Próxima". Selector de items por página.

**Estado vazio:**
- Ilustração ou ícone grande, frase "Nenhuma demanda encontrada com esses filtros" ou "Você ainda não tem demandas. Crie a primeira."
- CTA "Nova demanda".

**Mobile:**
- Filtros viram um botão "Filtros (3)" que abre full-sheet.
- Tabela vira lista de cards: cada card mostra Nº + Título + 2 badges (status, resultado) + responsável + data.

---

### Protótipo 5 — Formulário complexo (canônica: `/demandas/nova/`)

Cobre todos os `/nova/` e `/editar/`. Mostra os padrões mais difíceis.

**Estrutura:**
- Header: "Nova demanda" + botão "Cancelar" (volta para lista).
- Form em uma coluna no desktop (max-width ~720px), full-width no mobile.

**Seções (separadas por subtítulo + linha sutil):**

1. **Identificação**
   - Título (text, required)
   - Origem (radio: responsiva / proativa)
   - Tema (multi-select com chips; botão "+ Novo tema" abre **popup inline** para criar e auto-seleciona ao salvar)
   - Coordenação responsável (select)
   - Responsável (autocomplete server-side com debounce, mostra avatar + nome)
   - ☐ Marcar como restrita (CO+; ao marcar, mostrar tooltip explicando)

2. **Descrição**
   - Textarea grande (auto-resize, ~5 linhas iniciais)
   - Contador de caracteres no canto

3. **Partes envolvidas (formset dinâmico)**
   - Subseção "Pessoas": linha com autocomplete de pessoa + select de papel (com choices + opção "Outro" que revela campo de texto livre) + botão remover.
   - Botão "+ Adicionar pessoa" abaixo. Adiciona linha sem reload.
   - Subseção "Entidades": idêntica estrutura.
   - Para demanda **não-anônima**, exigir pelo menos 1 parte (mostrar mensagem de erro inline ao tentar salvar).

4. **Prazos** (opcional)
   - Data de início, data de prazo

5. **Anexos**
   - Drop zone "Arraste arquivos ou clique para escolher"
   - Lista de arquivos selecionados com nome + tamanho + ícone X para remover.
   - Validação inline: "Tipo não permitido", "Excede 25 MB".

**Rodapé fixo do formulário:**
- Botão primário "Salvar demanda"
- Botão secundário "Cancelar"
- Estado de loading no botão durante save.

**Erros:**
- Inline nos campos.
- `non_form_errors` dos formsets (ex.: "Pessoa duplicada na lista de partes") em banner no topo.

---

### Protótipo 6 — Detalhe rico (canônica: `/demandas/<uuid>/`)

A tela onde mora a maior parte do trabalho. Densa de informação, mas precisa respirar.

**Header:**
- Número em destaque (`MPD-2026-00042`, monospace, grande)
- Título da demanda (h1)
- Linha de meta: criada em DD/MM/AAAA por Fulano · atualizada em DD/MM/AAAA
- Badges: Status, Resultado, Restrita (se aplicável), Origem
- **CTA principal** (botão sólido, à direita do header):
  - Se responsiva e ainda não concluída: "Concluir demanda — devolutiva ao demandante" (abre drawer lateral, ver abaixo)
  - Se proativa e ainda não concluída: "Concluir ação"
  - Se concluída: botão sumido. Mostrar opção "Reabrir" em menu de mais.
- Menu kebab (⋮): Editar · Arquivar · Reabrir · Excluir (gated por permissão)

**Layout principal (desktop):**
Duas colunas. Coluna esquerda (66%):
- **Descrição** (texto da demanda, expansível se longo)
- **Timeline** — eventos cronológicos misturando interações + encaminhamentos + mudanças de estado (geradas automaticamente):
  - Cada item: ícone + tipo + autor + data/hora + conteúdo.
  - Itens de mudança de estado em estilo discreto (cinza, ícone pequeno).
  - Interações realizadas com fundo branco/card.
  - Interações agendadas em destaque âmbar com label "Agendada para DD/MM".
  - Devolutivas com selo "Devolutiva ao demandante".
  - Encaminhamentos como cards especiais (ofício enviado a órgão X, com status de resposta).
- **Botão "+ Adicionar interação"** ancorado ao final da timeline (abre form inline ou drawer).
- **Botão "+ Novo encaminhamento"** (mesma lógica).

Coluna direita (33%):
- **Partes envolvidas**: lista de pessoas e entidades com link, papel, e mini-avatar.
- **Encaminhamentos** (resumo): cards compactos com órgão, status, prazo. Link "Ver todos" se >3.
- **Anexos**: lista com ícone do tipo + nome + tamanho + botão baixar. Drop zone "+ Adicionar anexo" no fim.
- **Bloco Resultado** (se já classificado): badge grande + observação.

**Drawer lateral "Concluir demanda" (responsiva):**
- Abre lateralmente à direita (não modal — não cobre o conteúdo principal).
- Fecha por backdrop, Esc, ou botão X.
- Campos: Canal da devolutiva · Data da devolutiva · Conteúdo da devolutiva (textarea) · Resultado (select obrigatório, sem opção "pendente") · Observação (opcional).
- Validação inline.
- Botão "Concluir demanda" no rodapé. Loading ao salvar.

**Drawer lateral "Concluir ação" (proativa):**
- Mesma estrutura, mas sem campos de devolutiva. Apenas Resultado + Observação.

**Modal "Arquivar":**
- Aviso curto + checkbox de confirmação + botão "Arquivar".

**Modal "Reabrir":**
- "Reabrir esta demanda? Isso volta o status para 'em_andamento'." + botão.

**Mobile:**
- Single column (coluna direita vira seção abaixo da timeline).
- Drawer vira full-sheet bottom.

**Variações:**
- `/pessoas/<slug>/`: header (nome + meta) + cards de Contatos (telefones/emails/redes) + Endereço + Vínculos + Demandas relacionadas + Tags + Anexos. Sem timeline, sem CTA "Concluir".
- `/entidades/<slug>/`: idem, com Vínculos como seção central.

---

### Protótipo 7 — Pendências / Inbox

Padrão de **agrupamento temporal**.

**`/minhas-pendencias/`:**
- Header: "Minhas pendências" + contador ("8 pendências, 3 vencidas").
- Seções verticais agrupadas por horizonte:
  - **Vencidas** (borda vermelha à esquerda, expandida por padrão)
  - **Hoje**
  - **Amanhã**
  - **Esta semana**
  - **Próximas**
- Cada seção colapsa/expande.
- Cada item: tipo (ícone reunião/ligação/etc.) · título · demanda associada (link) · data/hora · botões "Marcar realizada" e "Cancelar".

**`/inbox/`:**
- Header: "Inbox" + contador.
- Filtros: Pendentes (default) · Processados · Descartados · Todos.
- Cada item: data de captura · texto capturado · **badges de envelhecimento** (âmbar +7d, vermelho +30d).
- Ações por item: "Processar" (verde, leva ao form de demanda pré-preenchido) · "Descartar" (vermelho, expande textarea de motivo inline).
- Estado vazio: ilustração + "Sua inbox está limpa. Capture algo com Ctrl+K."

**Mobile:**
- Lista vertical, cards full-width.
- Ações por item viram swipe ou botões dentro do card.

---

### Protótipo 8 — Painel de análise

**Rota:** `/analise/` (CO+)

**Header:**
- Título + filtro global (período: últimos 30d / 90d / 12 meses / custom)

**6 cards de métrica** (grid 2x3 no desktop, 1 coluna mobile):
1. Demandas por tema (doughnut → tabela)
2. Demandas por mês (line, últimos 12 meses → tabela)
3. Demandas por coordenação (bar → tabela)
4. Top 20 pessoas com mais demandas (tabela → bar)
5. Encaminhamentos pendentes por órgão (bar → tabela)
6. Carga por assessor (bar → tabela)

Cada card tem **toggle tabela ⇄ gráfico** no canto. Gráficos via Chart.js v4 (CDN), então usar paletas simples e legíveis.

**Auditoria (`/auditoria/`):** versão "lista rica" com:
- Filtros: usuário, modelo, ação (criou/editou/removeu), período.
- Lista com linha colapsável que ao clicar expande **diff visual** campo a campo (antes/depois com destaque verde/vermelho).

---

## 8. Design system esperado

Não precisa ser uma biblioteca completa — apenas o que aparece nos 8 protótipos, bem definido e nomeado.

### Componentes mínimos
- **Botão**: primário, secundário, perigo, ghost, link. Tamanhos sm/md/lg. Com ícone, só ícone, com loading.
- **Input texto**: default, focus, disabled, erro (com mensagem), com prefixo/sufixo.
- **Textarea**: auto-resize, contador.
- **Select** (nativo estilizado) e **Combobox** (autocomplete server-side).
- **Multi-select com chips**.
- **Checkbox**, **Radio**, **Toggle** (switch).
- **Badge**: cores semânticas, neutro, status, resultado, contador.
- **Chip**: filtro ativo (com X), tag colorida (11 cores fixas).
- **Card**: padrão e elevado.
- **Avatar**: imagem ou iniciais coloridas, tamanhos.
- **Modal**: centralizado, com backdrop.
- **Drawer**: lateral direito (desktop) e bottom-sheet (mobile).
- **Toast**: 4 variantes (sucesso/erro/aviso/info), empilhável.
- **Paginação**.
- **Tabs**.
- **Tooltip**.
- **Breadcrumb**.
- **Dropdown menu** (kebab e contextual).
- **Skeleton loaders** (linha de tabela, card, parágrafo).
- **Empty state**: ilustração/ícone + frase + CTA.
- **Banner inline**: erro de formulário (top do form).

### Padrões de interação
- **Hover** sutil em linhas clicáveis (background neutro 50).
- **Focus** visível em todos os controles (ring 2 colorido).
- **Loading**: botão com spinner inline, lista com skeleton, página inteira só em primeiro carregamento.
- **Confirmação destrutiva**: sempre via modal com botão de "Cancelar" mais proeminente que o de "Confirmar".

---

## 9. Microcopy e tom

- **Português brasileiro**, voz ativa, segunda pessoa quando útil ("Você ainda não tem demandas.")
- **Sem jargão técnico** ("registro" não, "demanda" sim).
- **Erros** explicam o que fazer ("Adicione pelo menos uma pessoa ou entidade como parte envolvida." — não "Required field.").
- **Botões** com verbo no infinitivo ("Salvar demanda", "Concluir ação", "Adicionar anexo").
- **Confirmações** descrevem consequência ("Arquivar esta demanda? Ela some das listas padrão mas pode ser reaberta.").

---

## 10. Entregáveis

**Formato preferencial:** Figma com:
- Auto-layout em componentes.
- Componentes nomeados de forma consistente (`Button/Primary/Medium`, `Badge/Status/EmAndamento`).
- **Tokens** publicados como variables (cores, espaços, tipografia).
- Páginas separadas por protótipo. Frames por viewport (desktop 1440px, mobile 390px).
- **Estados** explicitamente nomeados (frame "Lista de Demandas — vazia", "Lista de Demandas — com 50 itens").

**Aceitável (em ordem):**
1. Figma — formato ótimo, permite handoff direto.
2. HTML/CSS estático em uma pasta `prototipo/` — fidelíssimo, mas trabalhoso.
3. Penpot — equivalente Figma open-source, OK se for sua preferência.

**Não aceito:**
- PDF estático (perde estados/interações).
- Wireframes em baixa fidelidade.
- Print de Photoshop.

---

## 11. Critérios de aceite

O protótipo está pronto quando:
1. ✅ Os 8 protótipos estão desenhados em **desktop e mobile**.
2. ✅ Cada protótipo tem **pelo menos 3 estados** (padrão, vazio, erro).
3. ✅ Há uma página de **design system** com tokens e componentes nomeados.
4. ✅ A identidade visual (paleta + tipografia + tom) foi **validada com Pedro** numa rodada inicial antes de aplicar nos 8.
5. ✅ Microcopy está em português, com placeholders realistas (não Lorem ipsum).
6. ✅ Componentes são reutilizáveis (auto-layout no Figma, ou classes consistentes em HTML).
7. ✅ Estados de **status × resultado** da demanda estão visualmente diferenciados e legíveis para daltônicos (não só cor; usar também forma/texto).

---

## 12. Cronograma sugerido

Estimativa para alguém em dedicação parcial. Ajustar conforme disponibilidade.

| Fase | Entregável | Prazo sugerido |
|---|---|---|
| 1 | Direção visual (1 protótipo do shell + 1 lista + tokens) — validação com Pedro | Semana 1 |
| 2 | Protótipos 2–4 (Login, Home/Hub, Lista rica completa) | Semana 2 |
| 3 | Protótipos 5–6 (Form complexo, Detalhe rico) — os mais difíceis | Semanas 3–4 |
| 4 | Protótipos 7–8 (Pendências/Inbox, Análise) | Semana 5 |
| 5 | Polimento, mobile, estados, design system documentado | Semana 6 |

---

## 13. Documentação de apoio (este repositório)

Para entender o domínio em profundidade antes/durante o trabalho:

- [`roadmap.md`](../roadmap.md) — fases e critérios de aceite do produto.
- [`docs/mapa-de-telas.md`](mapa-de-telas.md) — todas as rotas formais.
- [`docs/modelo-de-dados.md`](modelo-de-dados.md) — schema, campos, validações.
- [`docs/fluxos-de-estado.md`](fluxos-de-estado.md) — transições válidas de status, resultado, etc.
- [`docs/permissoes.md`](permissoes.md) — matriz por perfil/ação.
- [`docs/decisoes.md`](decisoes.md) — ADRs (histórico de decisões).

**Não é obrigatório ler tudo.** O mapa-de-telas é o atalho mais útil; o resto é referência para tirar dúvidas pontuais.

---

## 14. Como tirar dúvidas

- Decisões de **produto** (nome de campo, comportamento, prioridade de tela) → perguntar para Pedro.
- Decisões de **implementação** (qual fonte, qual paleta, qual biblioteca) → carta branca, mas registrar no design system com justificativa.
- Mudanças que **contradigam** este briefing → discutir antes de aplicar (criar uma nova versão deste documento, não sobrescrever sem registro).

---

*Documento mantido em `docs/briefing-prototipo-frontend.md`. Última revisão: 2026-05-18.*
