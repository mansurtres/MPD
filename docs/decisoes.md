# MPD — Decisões Arquiteturais

Registro de decisões importantes tomadas no projeto. Cada entrada explica contexto, alternativas consideradas e justificativa. Em ordem cronológica.

> **Por que existe este documento:** decisões esquecidas viram fonte de bug e refactor. Registrar a justificativa em escrito permite que futuros mantenedores (ou você mesmo daqui a 2 anos) entendam por que algo foi feito assim, e mudem com conhecimento de causa.

---

## ADR 0001 — Stack tecnológica

**Data:** Planejamento inicial
**Status:** Aceito

### Contexto
Sistema deve rodar localmente sem custo, evoluir para web e potencialmente para SaaS comercial. Cliente é não-técnico; manutenibilidade do código importa. Desenvolvimento agêntico via Claude Code.

### Decisão
**Backend:** Python 3.12+ com Django 5.x.
**Banco:** PostgreSQL 16+.
**Frontend:** HTMX + Alpine.js + Tailwind CSS.
**Templates:** Django Templates (sem build pipeline complexo).
**Auditoria:** django-auditlog.
**Testes:** pytest + pytest-django + factory_boy.
**Lint/format:** ruff + black.
**Deps:** uv.

### Alternativas consideradas
- **FastAPI + React/Vue:** moderno, mas exige dois domínios de conhecimento e mais código para o mesmo resultado. Django + HTMX entrega 90% da experiência por 30% do esforço.
- **Rails:** menos suporte agêntico atual. Python tem ecossistema mais maduro para LLMs.
- **Flask:** menos baterias incluídas, decisões prematuras desnecessárias.
- **Node.js (Next.js):** complexidade de build pipeline incompatível com a meta de simplicidade.

### Justificativa
Django é "boring technology" — maduro, documentado, previsível, com admin embutido (porta dos fundos para inspeção desde dia 1), ORM e migrações consolidadas. PostgreSQL escala da casa do desenvolvedor até produtos comerciais sem reescrita. HTMX entrega UX moderna sem o peso de SPA.

### Consequências
- Curva de aprendizado curta para novos devs.
- Time-to-MVP rápido.
- Quando virar SaaS, infraestrutura já é compatível.
- Decisão de adicionar SPA (React/Vue) fica para v3.x se necessário.

---

## ADR 0002 — UUIDs como chave primária

**Data:** Planejamento inicial
**Status:** Aceito

### Contexto
Convenção comum no Django é usar `BigAutoField` (BIGSERIAL) como PK. Mas o sistema precisa preparar para multi-tenant futuro, e há cenários onde IDs sequenciais expõem informação (volume da base, ordem de cadastro).

### Decisão
Todos os modelos usam `UUIDField` como PK, gerado por `uuid4()`.

### Alternativas consideradas
- **BIGSERIAL:** mais simples, mais performático em índices, URLs mais curtas.
- **UUIDv7 (timestamp-ordered):** vantagens de UUID + ordenação temporal. Mas não é nativo no Django e adiciona complexidade.

### Justificativa
- **Privacidade:** competidor não consegue inferir volume da base ("cliente 47" vs "cliente 9842").
- **Multi-tenant futuro:** evita colisão ao migrar dados entre tenants.
- **Geração offline:** importação em lote, sync mobile futuro.
- **Custo:** performance penalty é negligível para o volume previsto (< 1M registros nos próximos anos).

### Consequências
- URLs ficam feias (`/casos/8a7f3...` em vez de `/casos/42`). Aceitável: usuários raramente compartilham URLs de registros internos.
- Banco fica ligeiramente maior. Aceitável.

---

## ADR 0003 — Sem multi-tenant no MVP

**Data:** Planejamento inicial
**Status:** Aceito

### Contexto
Sistema pode virar produto comercial (SaaS) onde cada cliente teria base isolada. Tentação de já modelar `tenant_id` em todas as tabelas para preparar.

### Decisão
**MVP é single-tenant.** Não há `tenant_id` em nenhuma tabela. Multi-tenant é decisão de v2.x quando virar produto comercial.

### Alternativas consideradas
- **Adicionar `tenant_id` em todas as tabelas desde o início:** prepara para futuro, mas polui schema, complica queries e exige decisões prematuras (compartilhamento de tags? de usuários? row-level security?).
- **Usar django-tenants:** biblioteca pronta para multi-tenant via schemas Postgres. Funciona bem, mas adiciona complexidade operacional desproporcional ao MVP.
- **Schema-per-tenant manual:** flexível mas exige mais código.

### Justificativa
"Dados separados do código" (princípio do projeto) significa configuração via `.env`, não multi-tenancy de schema. Adicionar `tenant_id` depois é uma migration simples; antecipar agora cobra preço todo dia.

### Consequências
- Quando virar SaaS, primeira tarefa de v2.x é decidir estratégia (schema-per-tenant via django-tenants, ou row-level via `tenant_id`) e migrar.
- Cada cliente que adotar antes do v2.x roda instância dedicada (`docker compose up`).

---

## ADR 0004 — Endereço inline em Cidadão e Entidade

**Data:** Planejamento inicial
**Status:** Aceito

### Contexto
CRMs maduros (CiviCRM) têm tabela `Address` separada, permitindo múltiplos endereços por contato (residencial, comercial, billing). Modelar assim desde o MVP?

### Decisão
**Endereço inline em `Cidadao` e `Entidade`** (campos `cep`, `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `estado` na própria tabela). Um endereço por pessoa/entidade no MVP.

### Alternativas consideradas
- **Tabela `enderecos` separada com FK:** flexível para múltiplos endereços, mas exige JOIN em toda listagem.

### Justificativa
99% dos cidadãos terão um único endereço relevante. JOIN extra em toda query é custo recorrente; tabela separada para um único registro 99% das vezes é YAGNI.

### Consequências
- Quando aparecer caso real de cidadão com múltiplos endereços (residencial + comercial relevantes para o mandato), refatorar é uma migration: mover campos para nova tabela `enderecos` com FK. Custo conhecido, isolado, e só pago quando o problema existir.

---

## ADR 0005 — Tabela `tags` única e compartilhada

**Data:** Planejamento inicial
**Status:** Aceito

### Contexto
Cidadãos, entidades e casos precisam ser classificáveis por temas, perfis, território, etc. Modelar tags separadas para cada entidade ou unificar?

### Decisão
**Uma única tabela `tags`** com campo `categoria` (`tema`, `perfil`, `territorio`, `livre`). M:N com cidadãos, entidades, casos.

### Alternativas consideradas
- **Tags separadas por entidade:** `tags_cidadao`, `tags_caso`, `tags_entidade`. Mais "puro" semanticamente, mas triplica curadoria.
- **Tags hierárquicas desde o início:** rica, mas inflaciona MVP.

### Justificativa
Tag de "tema" usada num cidadão (área de interesse dele) é a mesma tag usada num caso (área temática da demanda). Unificar simplifica curadoria, mesclagem (v0.6) e busca.

### Consequências
- Categoria distingue uso semântico sem fragmentar tabelas.
- Tag hierárquica (parent_id) entra em v1.x se a equipe sentir necessidade.

---

## ADR 0006 — Tema do caso é uma tag, não campo dedicado

**Data:** Planejamento inicial
**Status:** Aceito

### Contexto
Casos precisam ser classificados por tema (saúde, mobilidade, educação). Criar campo enum/FK dedicado ou usar o sistema de tags?

### Decisão
**Tema é uma tag de categoria `tema`** vinculada ao caso. Filtros consultam pela categoria. Sem campo dedicado.

### Alternativas consideradas
- **`tema_id` como FK direta para tags:** redundante.
- **Enum hardcoded:** rígido demais, exige migration para adicionar tema novo.
- **CharField livre:** dá liberdade, mas perde estrutura para análise.

### Justificativa
A taxonomia de temas evolui com o mandato. Tag oferece flexibilidade total (criar, mesclar, hierarquizar) sem migrations. Custo de query é equivalente.

### Consequências
- Frontend precisa filtrar tags por categoria nas listagens "tema".
- Algumas queries ficam mais complexas (JOIN extra em vez de campo direto).
- Aceitável pelo ganho em flexibilidade.

---

## ADR 0007 — Visibilidade simplificada por boolean `restrito`

**Data:** Planejamento inicial
**Status:** Aceito

### Contexto
Casos sensíveis (violência, saúde mental, denúncia) precisam ter visibilidade restrita. Modelar como?

### Decisão
**Um único campo boolean `restrito`** em `Caso`. Quando `TRUE`, visível apenas para responsável, Chefe de Gabinete e Administrador.

### Alternativas consideradas
- **Combinação `visibilidade` + `nivel_sensibilidade`** com 3 valores cada: 9 estados teóricos, semântica difusa.
- **Lista de `acesso_explicito`** (M:N com Usuario): granularidade total, mas complexidade alta.

### Justificativa
Simplicidade. "Caso restrito" é semântica clara: só quem precisa ver, vê. Combinatória de níveis cria complexidade sem benefício real.

### Consequências
- Quando aparecer demanda real de granularidade maior (alguns casos visíveis para CO mas não para AS), reavaliar. Refactor: substituir boolean por enum ou tabela de ACL.

---

## ADR 0008 — Auditoria via biblioteca, não modelo próprio

**Data:** Planejamento inicial
**Status:** Aceito

### Contexto
Sistema precisa registrar mudanças (criação, edição, exclusão) em entidades críticas. Modelar tabela `LogAuditoria` própria ou usar biblioteca?

### Decisão
Usar **`django-auditlog`**. Configurada nos modelos `Cidadao`, `Entidade`, `Vinculo`, `Caso`, `Encaminhamento`, `Anexo`, `Usuario`, `SolicitacaoLGPD`.

### Alternativas consideradas
- **Tabela própria com signals manuais:** controle total, mas reinvenção.
- **`django-simple-history`:** alternativa popular. Mais pesada (cria tabelas espelho com cada versão).

### Justificativa
`django-auditlog` é maduro, testado em produção em muitos projetos, gratuito. Cria tabela `auditlog_logentry` única com diff em JSONB. Apenas adiciona campos necessários, não infla schema.

### Consequências
- Dependência externa adicional, mas estável e bem mantida.
- Schema da tabela auditlog não está sob nosso controle direto. Aceitável.

---

## ADR 0009 — Quatro perfis, distinção Coord por coordenação assumida

**Data:** Planejamento inicial
**Status:** Aceito

### Contexto
Mandato tem Chefe de Gabinete, Coord. Jurídico, Coord. de Comunicação, e Assessores. Modelar como cinco grupos ou consolidar?

### Decisão
**Quatro perfis:** Administrador, Chefe de Gabinete, Coordenador, Assessor. Distinção entre Coord. Jurídico e Coord. de Comunicação **não é grupo separado** — é dada pela `coordenacao_responsavel` que assumem nos casos.

### Alternativas consideradas
- **Cinco grupos** (com Coord. Jurídico e Coord. Comunicação separados): mais explícito, mas duplica matriz de permissões e cria fricção quando alguém troca de coordenação.
- **Permissões individualizadas (sem grupos):** flexível, mas inviável de manter.

### Justificativa
Permissões de Coord. Jurídico e Comunicação são idênticas; só muda a área onde atuam. Modelar isso como duas coordenações de casos (`coordenacao_responsavel`) é mais econômico que duplicar grupos.

### Consequências
- Promover Assessor a Coordenador é trocar grupo, sem worry sobre qual coordenação específica.
- Quando virar produto comercial e clientes tiverem estruturas diferentes (3 coordenações? 5?), basta configurar lista em settings.

---

## ADR 0010 — Status `agendada` em Interação (anti-perda de rastreabilidade)

**Data:** Após análise do código do CiviCRM
**Status:** Aceito

### Contexto
Necessidade central do sistema: nenhuma demanda pode se perder. Como garantir isso estruturalmente, não apenas por disciplina humana?

### Decisão
Interação tem campo `status` com valores `realizada`, `agendada`, `cancelada`. **Interação pode existir no futuro.** Quando uma interação é encerrada, formulário oferece criar interação de follow-up agendada.

### Alternativas consideradas
- **Tabela separada `tarefas` ou `lembretes`:** duplica conceito. Interação já é um evento no tempo; faltava só permitir tempo futuro.
- **Status `pendente` no Caso:** confunde estado do trabalho com estado das ações pontuais.

### Justificativa
Inspirada no CiviCRM (`civicrm_activity` com status `Scheduled`). Cada interação encerrada **tende** a gerar a próxima, criando sistema autossustentável de rastreabilidade. Ações futuras são visíveis como "vencidas" se não executadas.

### Consequências
- Modelo de Interação ganha campo `status` e `interacao_origem_id` (para cadeias de follow-up).
- UI tem nova tela "Minhas Interações Pendentes".
- Defesa contra esquecimento sai do humano e entra no sistema.

---

## ADR 0011 — Mudanças no Caso geram interações automáticas

**Data:** Após análise do código do CiviCRM
**Status:** Aceito

### Contexto
Caso tem histórico de mudanças (status, responsável, arquivamento). Onde registrar isso? Tabela de auditoria do caso? Campo no caso? Outra solução?

### Decisão
**Mudanças relevantes no Caso geram interações automáticas** na timeline (tipo `mudanca_status`, `mudanca_responsavel`, `arquivamento`, `registro_inicial`). Implementadas via signal `post_save`. Marcadas com `automatica=TRUE`.

### Alternativas consideradas
- **Tabela `historico_caso` separada:** mais "limpo", mas fragmenta a história em duas tabelas.
- **Confiar apenas em `django-auditlog`:** funciona para auditoria técnica, mas integração visual com timeline é ruim.

### Justificativa
Inspirada no CiviCase (`Open Case`, `Change Case Status` como activities). História do caso vira parte natural da timeline. Eliminamos uma tabela, melhoramos UX, mantemos integridade.

### Consequências
- Timeline mostra interações manuais e automáticas, distinguidas visualmente.
- Auditoria via `django-auditlog` continua existindo para fins técnicos (quem editou o quê), mas timeline é a fonte para narrativa do caso.

---

## ADR 0012 — Communication preferences como booleans no Cidadão

**Data:** Após análise do código do CiviCRM
**Status:** Aceito

### Contexto
LGPD exige respeitar oposição ao tratamento (art. 18). Cidadão pode pedir para não receber emails, ligações, SMS. Modelar como?

### Decisão
**Quatro booleans em Cidadão:** `nao_telefonar`, `nao_enviar_email`, `nao_enviar_sms`, `nao_compartilhar_dados`. Default `FALSE`. Comunicações em massa respeitam essas flags antes de enviar.

### Alternativas consideradas
- **Tabela separada `preferencias_comunicacao`:** overkill para 4 booleans.
- **Campo JSON `preferencias`:** flexível mas sem validação estrutural.

### Justificativa
Inspirada nos campos `do_not_phone`, `do_not_email` etc. do CiviCRM. Estrutura simples, validação no nível do código de envio (não no banco), atende LGPD.

### Consequências
- Quando newsletter entrar (v1.x), respeitar `nao_enviar_email = TRUE` é obrigatório.
- WhatsApp/SMS em massa respeitam `nao_enviar_sms`.
- Não bloqueia comunicação direta de caso (uma resposta a uma demanda específica não é "comunicação em massa").

---

## ADR 0013 — Reunião como Interação tipo `reuniao`, não módulo Agenda

**Data:** Conversa de alinhamento com o cliente
**Status:** Aceito

### Contexto
Cliente reconhece que reuniões e eventos podem se relacionar com casos ou cidadãos. Criar módulo "Agenda" próprio ou aproveitar Interação?

### Decisão
**No MVP, reunião agendada é uma Interação tipo `reuniao` com `status='agendada'`** vinculada a um caso. Aparece tanto na timeline do caso quanto em "Minhas próximas reuniões". Módulo "Agenda" como visão dedicada (com calendário, integração Google Calendar) fica para v2.x.

### Alternativas consideradas
- **Tabela `eventos_agenda` separada desde MVP:** complexidade prematura. Reunião dentro de caso já cobre 90% dos casos.
- **Não modelar reuniões no MVP:** perde rastreabilidade.

### Justificativa
Reunião é uma interação como qualquer outra, com data e participantes. Aproveitar a estrutura existente economiza modelo, código e UX duplicados. Módulo "Agenda" futuro será apenas uma visão consolidada que agrupa esses eventos com calendário visual.

### Consequências
- Reuniões sem caso vinculado (ex: agenda pessoal do parlamentar) não cabem no MVP. Aceitável: agenda pessoal vive em Google Calendar até v2.x.
- Quando v2.x chegar, eventos podem ganhar entidade própria com FK opcional para Caso/Cidadão/Entidade.

---

## ADR 0014 — Proposições legislativas só em v2.x, mas arquitetura prepara

**Data:** Conversa de alinhamento com o cliente
**Status:** Aceito

### Contexto
Cliente sinaliza que evolução natural do MPD é controle e geração de instrumentos legislativos (PL, RI, indicação, moção). Modelar agora?

### Decisão
**Não no MVP.** Modelar Proposição é v2.x. Mas arquitetura atual deve permitir vínculo futuro N:N entre Proposição e Caso sem refactor pesado.

### Alternativas consideradas
- **Modelar Proposição já no MVP:** duplica esforço sem entregar valor imediato.
- **Esquecer Proposição até v2.x:** corre o risco de criar amarrações que dificultem a evolução.

### Justificativa
Princípio "construir o que é necessário agora, deixar portas abertas para o futuro". Tabela `Caso` já tem ID UUID estável; futura `Proposicao` pode ter FK para Caso ou tabela associativa M:N sem mexer em nada existente.

### Consequências
- v2.x adiciona modelo `Proposicao` com tipo, número, data, status na tramitação, e tabela associativa `proposicao_caso` (M:N).
- v3.x adiciona "motor de minutas" — geração assistida via templates (possivelmente com Claude API).

---

## ADR 0015 — Inbox dentro do app `casos`, não app separado

**Data:** Revisão de arquitetura para enxugamento
**Status:** Aceito

### Contexto
Inbox de captura rápida (GTD) é funcionalidade central. Modelar como app Django próprio (`apps/inbox/`) ou dentro de outro?

### Decisão
**ItemInbox vive em `casos/models.py`.** Não há app `inbox` separado.

### Alternativas consideradas
- **App `inbox` próprio:** mais "puro" arquiteturalmente.
- **App `core`:** menos coeso semanticamente.

### Justificativa
Inbox existe em função de gerar casos. Sua relação com `Caso` é íntima (cada item processado vira um caso). Separar em app gera fronteira artificial e quebra coesão. Princípio: arquitetura segue uso, não preferências teóricas.

### Consequências
- App `casos` tem 5 modelos: `Caso`, `Interacao`, `Encaminhamento`, `Anexo`, `ItemInbox`. Aceitável.
- Se o inbox crescer ao ponto de ter funcionalidades além de gerar casos (ex: integração com WhatsApp inbound em v3.x), aí pode virar app próprio.

---

## ADR 0016 — Sistema serve mandato pensando em campanha (e múltiplas campanhas)

**Data:** Conversa de alinhamento com o cliente
**Status:** Aceito

### Contexto
Sistema é para o mandato ou para campanhas? Inicialmente houve cautela jurídica excessiva sobre "muralha" entre os dois.

### Decisão
**Sistema serve ao mandato, com olhar para a continuidade política do agente.** Não há "muralha" técnica entre uso institucional e político — há disciplina contextual: comunicação em massa em período eleitoral exige cuidados próprios, mas a base de relacionamento é única e contínua, propriedade do agente político (não da Câmara).

### Justificativa
Cliente esclareceu (e fez sentido): mandato é veículo, continuidade política é objetivo. Manter base, registrar histórico, acompanhar quem procurou e por quê é exercício legítimo. Restrições são específicas (disparo em massa em período eleitoral) e aplicam-se ao uso, não ao registro.

### Consequências
- Sistema é propriedade do Pedro como pessoa física. Não pertence à Câmara Municipal.
- Em períodos eleitorais, certas funcionalidades (newsletter, disparo em massa) terão regras de uso específicas — implementadas em v1.x quando a feature existir.
- Exit strategy garantida: dados sempre exportáveis, sistema migrável.

---

## ADR 0017 — Status e Resultado como dimensões independentes do Caso

**Data:** Conversa de alinhamento com o cliente
**Status:** Aceito

### Contexto
Versão inicial do modelo tinha apenas `status='respondido'` para indicar que o caso foi fechado com retorno ao cidadão. Cliente identificou que isso confunde dois eventos distintos: **o mandato cumpriu o dever de fechar o ciclo** (sempre obrigatório) e **a demanda obteve sucesso material** (variável).

A confusão tem custo político real: sem essa distinção, o sistema não consegue responder perguntas como "quais cidadãos viram o mandato resolver algo concreto na vida deles?" — pergunta cuja resposta é a base do relacionamento eleitoral autêntico.

### Decisão
Adicionar campo `resultado` no `Caso`, **independente de `status`**:

- `pendente` — default. Ainda não há desfecho conhecido.
- `atendido` — demanda resolvida, cidadão obteve o que pediu.
- `atendido_parcialmente` — resolução parcial.
- `nao_atendido` — tentativa frustrada.
- `inviavel` — mostrou-se impossível de atender (fora de competência, juridicamente impossível). Distingue de `nao_atendido`: nem se tentou porque não cabia.
- `nao_se_aplica` — categoria de avaliação não cabe (casos proativos sem dimensão de "atendimento": postagens, discursos, manifestações por convicção política).

E campo `resultado_observacao` (TEXT) para anotação interna sobre o desfecho.

**Regra de fechamento atualizada:** `status='respondido'` exige `resultado ≠ 'pendente'` (além das condições anteriores: `retorno_data` e `retorno_conteudo`).

**Mudanças em `resultado` geram interação automática** na timeline (tipo `mudanca_resultado`), preservando histórico de avaliações sucessivas.

### Alternativas consideradas
- **Refinar `status` com mais valores** (`respondido_atendido`, `respondido_nao_atendido`, etc.): explosão combinatória, mistura semântica de duas dimensões diferentes.
- **Apenas dois valores** (`atendido` / `nao_atendido`): perde a riqueza de "parcialmente atendido" (cenário muito comum) e "inviável" (juridicamente diferente de "não conseguimos").
- **Quatro valores** (sem `nao_se_aplica`): forçaria casos proativos puramente comunicacionais a se classificarem como atendido/não-atendido, distorcendo análises.
- **Cinco valores** (sem `nao_se_aplica`): cliente identificou que casos proativos sem dimensão avaliativa precisam de saída honesta. `nao_se_aplica` resolve.

### Justificativa
A separação entre status (ciclo do trabalho) e resultado (desfecho material) viabiliza inteligência política do sistema:

- Identificar bairros, temas, canais com maior/menor índice de efetividade.
- Identificar cidadãos com casos atendidos — pessoas que viram o mandato resolver algo concreto na vida delas.
- Cruzar resultado × tema × responsável em painel analítico.
- Fila operacional valiosa: casos com resultado conhecido mas sem retorno comunicado ainda ao cidadão.

`nao_se_aplica` é compromisso entre flexibilidade (acomoda iniciativas sem dimensão de atendimento) e disciplina (continua exigindo classificação explícita ao fechar). Risco de uso indevido (escolher como atalho para evitar dizer "não atendido") mitigado por: posicionamento na UI (último, separado visualmente) e visibilidade gerencial via painel analítico.

### Consequências
- Tabela `casos` ganha duas colunas: `resultado` e `resultado_observacao`.
- `clean()` do model passa a validar `resultado ≠ 'pendente'` quando `status='respondido'`.
- Tipo `mudanca_resultado` adicionado às interações automáticas.
- Painel de análise (Fase 5) ganha visões cruzando status × resultado, dimensões por tema/bairro/coordenação, e lista de "cidadãos com casos atendidos".
- Tela de detalhe do caso ganha o campo, posicionado próximo aos campos de retorno.

---

*Decisões adicionadas em ordem cronológica conforme surgem. Cada decisão registrada uma vez; alterações futuras criam nova ADR (não editam a anterior).*
