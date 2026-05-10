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

---

## ADR 0018 — Renomeação: Cidadão → Pessoa, Caso → Demanda

**Data:** 2026-05-07
**Status:** Aceito

### Contexto
Os termos originais "Cidadão" e "Caso" foram questionados antes do início da codificação dos modelos.

"Cidadão" tem conotação de gênero em português (masculino padrão) e limita o escopo semântico a cidadãos formais, quando o mandato se relaciona com qualquer pessoa — incluindo grupos informais, representantes, colaboradores.

"Caso" remete a atendimento jurídico ou serviço social, não ao vocabulário real do gabinete parlamentar municipal.

### Decisão
- **`Cidadao` → `Pessoa`** (model, tabela `pessoas`, rotas `/pessoas/`)
- **`Caso` → `Demanda`** (model, tabela `demandas`, rotas `/demandas/`)

Apps Django permanecerão com os nomes `cidadaos` e `casos` até o início da Fase 2, quando serão renomeados para `pessoas` e `demandas` antes da criação dos primeiros models — custo mínimo enquanto `models.py` ainda está vazio.

### Alternativas consideradas
- **Contato** (em vez de Pessoa): jargão de CRM de vendas, inadequado para representação política.
- **Manter Cidadão:** preserva os nomes originais, mas carrega gênero gramatical embutido.
- **Manter Caso:** amplamente compreendido, mas desconexo do vocabulário do gabinete.

### Justificativa
"Pessoa" é neutral, humanizante, e alinha com o vocabulário jurídico brasileiro ("Pessoa Física" × "Pessoa Jurídica"). "Demanda" é o termo exato usado no dia a dia de um mandato parlamentar municipal para descrever o que um cidadão traz ao gabinete.

### Consequências
- Todos os docs, rotas, templates e models usam os novos nomes.
- Renomear os apps Django é tarefa inicial da Fase 2 (antes de criar qualquer migration nos apps afetados).

---

## ADR 0019 — M:N entre Demanda e Partes (Pessoas e Entidades)

**Data:** 2026-05-07
**Status:** Aceito

### Contexto
No design original, `casos` tinha duas FKs simples: `cidadao_id` (um único cidadão) e `entidade_id` (uma única entidade). Isso impede registrar demandas que envolvem múltiplos solicitantes — cenário comum no dia a dia do mandato (grupo de vizinhos solicitando reparo de rua, família requerendo benefício social, etc.).

### Decisão
Substituir as FKs simples por duas tabelas de junção:

- **`demanda_pessoas`** (`demanda_id`, `pessoa_id`, `papel`, `observacao`, `criado_em`) — UNIQUE em `(demanda_id, pessoa_id)`.
- **`demanda_entidades`** (`demanda_id`, `entidade_id`, `papel`, `observacao`, `criado_em`) — UNIQUE em `(demanda_id, entidade_id)`.

Campo `papel` (texto livre) registra o papel da parte naquela demanda específica: "solicitante", "afetado", "representante", etc.

A constraint "pelo menos uma parte ou anônimo" é validada no formulário/view, não no banco (pois envolve M:N).

### Alternativas consideradas
- **Tabela única `demanda_partes` polimórfica:** um GenericForeignKey apontando para Pessoa ou Entidade. Economiza uma tabela, mas perde FK real e torna queries menos legíveis. Descartado em favor de clareza.
- **Manter FKs simples:** solução adequada para mandatos com demandas de solicitante único, mas insuficiente para a realidade política onde múltiplos representantes comparecem juntos.

### Justificativa
M:N é a multiplicidade real do domínio. Duas FKs reais > uma GenericFK na junção. Três linhas similares > abstração prematura.

### Consequências
- Demanda não tem mais `cidadao_id` nem `entidade_id` diretos.
- Queries "demandas de uma pessoa" passam por JOIN em `demanda_pessoas`.
- Telas de detalhe de Pessoa e Entidade listam demandas via esse JOIN.
- Formulário de nova demanda inclui seção de partes com seleção múltipla.

---

## ADR 0020 — Anexos polimórficos via GenericForeignKey

**Data:** 2026-05-07
**Status:** Aceito

### Contexto
O design original tinha `anexos.caso_id FK → casos` — anexos só podiam ser pendurados em demandas. Necessidade identificada: anexar documentos também a Pessoas (identidade, comprovante), Entidades (CNPJ, estatuto), Encaminhamentos (ofício enviado, resposta recebida).

### Decisão
Substituir a FK simples por **`GenericForeignKey`** do Django (via `django.contrib.contenttypes`):

```python
content_type = ForeignKey(ContentType, on_delete=CASCADE)
object_id    = UUIDField()
content_object = GenericForeignKey('content_type', 'object_id')
```

Entidades que aceitam anexos no MVP: `Demanda`, `Pessoa`, `Entidade`, `Encaminhamento`.

### Alternativas consideradas
- **FK específica por entidade** (`demanda_anexos`, `pessoa_anexos`, etc.): FK real, integridade garantida pelo banco. Mas exige nova tabela (e nova migration) para cada entidade futura. Cresce linearmente com o schema.
- **Manter apenas `caso_id`:** limita a capacidade do sistema; documentos de pessoa e encaminhamento ficariam "soltos" na demanda sem identificação.

### Justificativa
Padrão consolidado no Django e em CRMs maduros (CiviCRM usa `entity_id` + `entity_table` exatamente assim). O custo (sem integridade referencial de banco) é coberto por signal `pre_delete` nos models vinculados, que exclui anexos órfãos antes de deletar o registro pai.

### Consequências
- Tabela `anexos` passa a ter `content_type_id` e `object_id` em vez de `demanda_id`.
- Índice composto `(content_type_id, object_id)` para lookup eficiente.
- Signal `pre_delete` necessário em `Demanda`, `Pessoa`, `Entidade`, `Encaminhamento`.
- Upload disponível no detalhe de qualquer dessas entidades, não apenas da demanda.

---

## ADR 0021 — Entidade como agrupamento universal

**Data:** 2026-05-07
**Status:** Aceito

### Contexto
O design original de `entidades` modelava apenas organizações formais: associações, sindicatos, empresas — tipos com CNPJ e endereço formal. O mandato municipal, porém, precisa registrar relacionamentos com agrupamentos informais: "Família Silva", "Turma do WhatsApp do Bairro X", "Moradores da Quadra 7".

### Decisão
Expandir o CHECK do campo `tipo` em `entidades` para incluir agrupamentos sem formalidade jurídica:

```
Novos tipos adicionados:
  familia        — grupo familiar sem CNPJ
  grupo_informal — coletivo sem estrutura formal (grupo de WhatsApp, vizinhança)
  condominio     — condomínio residencial (com ou sem CNPJ)
```

Nenhuma mudança estrutural na tabela — todos os campos além de `nome` e `tipo` já eram opcionais. O CNPJ permanece UNIQUE NULLS DISTINCT (múltiplos registros sem CNPJ não conflitam).

### Alternativas consideradas
- **Tabela separada `grupos`:** mais puro semanticamente, mas fragmenta o cadastro e o relacionamento M:N com Demanda.
- **Manter Entidade apenas para formal:** impede registrar vínculos reais do mandato com famílias e grupos informais, que são atores políticos relevantes.

### Justificativa
A tabela `entidades` já suportava o caso tecnicamente (campos opcionais). A mudança é apenas semântica (expandir o tipo). "Família Silva" como entidade do tipo `familia` é mais rico politicamente do que deixar esse vínculo sem registro.

### Consequências
- `tipo` aceita `familia`, `grupo_informal`, `condominio` além dos tipos originais.
- Entidades informais tipicamente terão só `nome` e `tipo` preenchidos — tudo mais é opcional.
- UI pode filtrar por tipo para separar formais de informais nas listagens.

---

---

## ADR 0022 — Sistema de permissões modular via Django Groups + Permissions nativos

**Data:** 2026-05-08
**Status:** Aceito

### Contexto
A pergunta pendente desde a Fase 0: implementar 4 perfis fixos (ADM, CG, CO, AS) com lógica de permissão hardcoded em Python, ou construir um sistema mais flexível?

Pedro clarificou: o sistema precisa ser **capaz** de criar perfis diferentes, com permissões e acessos diferentes. Qualquer ação pode ser permissionada ou impedida. A modularidade de acesso é o requisito central — não os 4 perfis específicos.

### Decisão

Usar o **sistema nativo de `Permission` + `Group` do Django** em sua capacidade plena:

1. **Permissões granulares por model**: cada model gera automaticamente 4 permissões (`add_X`, `change_X`, `delete_X`, `view_X`). Permissões customizadas são declaradas em `Meta.permissions` para ações específicas (ex: `('can_archive_demanda', 'Pode arquivar demandas')`, `('can_anonymize_pessoa', 'Pode anonimizar pessoas')`).

2. **Groups como perfis configuráveis**: `Group` do Django é o perfil. Grupos são criados via data migration com a configuração padrão (equivalente à matriz em `docs/permissoes.md`), mas podem ser alterados pelo ADM sem deploy novo.

3. **Checks via `user.has_perm()`**: toda verificação de permissão usa `user.has_perm('app.codename')`. Não há `if grupo == 'Chefe de Gabinete':` no código.

4. **Helpers em `core/permissions.py`**: funções como `pode_ver_demanda(user, demanda)` continuam existindo, mas internamente chamam `has_perm` + regras de negócio (como o campo `restrito`), nunca checam nome de grupo diretamente.

5. **Configuração inicial via data migration na Fase 1**: cria 4 grupos padrão (Administrador, Chefe de Gabinete, Coordenador, Assessor) com as permissões da matriz documentada. Esses grupos são o ponto de partida, não o teto.

### Alternativas consideradas

- **4 grupos hardcoded com `if grupo == 'X':`**: simples de implementar, mas rígido. Adicionar um 5º grupo exigiria alteração de código em vez de configuração. Descartado.
- **Permissões por linha de objeto (row-level security)**: granularidade máxima, mas complexidade alta. O campo `restrito` em Demanda já cobre o caso central de row-level. Reservado para v2.x.

### Justificativa

O sistema nativo do Django foi projetado exatamente para isso: grupos e permissões configuráveis sem redeployment. Usar a infraestrutura existente em vez de reinventá-la é o princípio "simplicidade vence". O ADM pode criar "Grupo Estagiário" com acesso só-leitura sem tocar em código.

### Consequências

- Fase 1 cria 4 grupos via data migration com permissões da matriz.
- `core/permissions.py` usa `has_perm`, não checagem de nome de grupo.
- Novas permissões customizadas entram no `Meta.permissions` de cada model conforme necessidade.
- ADM pode criar/editar grupos pelo Django Admin (e futuramente pela UI própria em v1.x).
- `docs/permissoes.md` documenta a configuração **padrão** — não uma regra inviolável de código.

---

## ADR 0024 — Timing dos grupos: Fase 2, não Fase 1 (emenda ADR 0022)

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

ADR 0022 estabeleceu que "Fase 1 cria 4 grupos via data migration com permissões da matriz". Ao revisar o escopo da Fase 1, identificou-se uma contradição: as permissões customizadas que esses grupos deveriam ter (`pode_criar_demanda`, `pode_ver_todas_demandas`, etc.) são declaradas no `Meta` dos models `Pessoa`, `Demanda`, `Interacao`, etc. — que só existem nas Fases 2 e 3. Criar os grupos na Fase 1 geraria caixas vazias sem permissões significativas.

Além disso, Pedro questionou a necessidade de 4 perfis pré-definidos no MVP, o que levou a um redesenho do escopo da Fase 1.

### Decisão

**Fase 1** usa apenas `is_staff=True` para distinguir quem pode gerenciar outros usuários. Nenhum Group criado.

**Fase 2** cria os 4 grupos padrão (Administrador, Chefe de Gabinete, Coordenador, Assessor) via data migration, com as permissões dos models `pessoas` (`Pessoa`, `Entidade`, `Vinculo`, `Tag`).

**Fase 3** expande as permissões dos grupos via data migration com as permissões customizadas dos models `demandas`.

### Justificativa

Grupos criados junto com os models que protegem têm conteúdo real e testável imediatamente. Grupos criados antecipadamente são configuração sem verificação. O Django já suporta atribuição direta de permissões a usuários individuais via Admin — suficiente para o período entre Fase 1 e Fase 2.

### Consequências

- Fase 1 entrega apenas infraestrutura de autenticação. Nenhuma data migration de grupos.
- Fase 2 inclui step de criação de grupos como parte do setup dos models de pessoas.
- Fase 3 inclui step de expansão das permissões como parte do setup dos models de demandas.
- ADR 0022 permanece válida em tudo exceto no timing.

---

## ADR 0025 — BigAutoField como PK universal (supersede ADR 0002)

**Data:** 2026-05-08
**Status:** Aceito (supersede ADR 0002)

### Contexto

ADR 0002 prescreveu `UUIDField` como PK em todos os models. Na Fase 1, o model `accounts.Usuario` foi implementado com a default do Django (`BigAutoField`) sem que o desvio fosse questionado. A Fase 2 agora introduz quatro novos models (`Pessoa`, `Entidade`, `Vinculo`, `Tag`) e exige uma decisão antes de criar as primeiras migrations: seguir o doc (UUID nos novos, mas Usuario seguiria com BigAutoField — schema misto), retroceder o Usuario para UUID (drop+recreate, perde a base de dev), ou padronizar todo o schema com BigAutoField.

### Decisão

**Padronizar `BigAutoField` em todos os models do MVP.** Atualizar ADR 0002 como supersedida.

### Justificativa

- **Consistência:** schema misto (UUID em pessoas, int em usuario) gera fricção em FKs cruzadas e confunde quem lê o código.
- **Custo dos benefícios do UUID é especulativo:** os ganhos de privacidade (URL não revela volume) e geração offline mencionados em ADR 0002 são features que o MVP não usa nem usará tão cedo. Multi-tenant é v2.x — quando chegar, é uma migration.
- **Custo do BigAutoField é zero hoje:** menor índice, URLs curtas, integração mais simples com bibliotecas (django-auditlog, formulários, etc).
- **Reversível:** se um dia houver razão real (ex.: API pública em v3.x), trocar PK é uma migration por tabela. Antecipar agora cobra preço todo dia.

### Consequências

- Models de Fase 2 e seguintes usam o default do Django (`BigAutoField`, configurado em `DEFAULT_AUTO_FIELD`).
- ADR 0002 fica registrada para histórico, mas não é mais a regra vigente.
- Documento `docs/modelo-de-dados.md` será atualizado para refletir BigAutoField nas tabelas (mudança de tipo de PK e FK que apontam para `usuarios(id)`).

---

## ADR 0023 — Política de senha: mínimo 8 chars, sem complexidade obrigatória

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

A decisão inicial (roadmap v0.2) definia mínimo de 12 caracteres para senhas, adotada sem discussão com Pedro. Ao revisar a Fase 1, Pedro sinalizou que não participou da decisão e queria reavaliá-la.

O sistema serve uma equipe interna pequena, de perfil não-técnico, em um mandato municipal. Exigências de complexidade (maiúsculas, números, caracteres especiais) criam atrito de adoção sem benefício proporcional para esse contexto.

### Decisão

Remover os validadores `UserAttributeSimilarityValidator` e `NumericPasswordValidator` do Django. Manter apenas:

- **`MinimumLengthValidator`** com `min_length=8`.
- **`CommonPasswordValidator`** — bloqueia senhas trivialmente comuns ("password", "12345678", etc.) sem exigir complexidade específica.

Sem exigência de maiúsculas, números ou caracteres especiais. Sem bloqueio por similaridade com o nome de usuário.

### Alternativas consideradas

- **12 caracteres + validadores padrão (decisão original):** mais seguro em cenário web com usuários desconhecidos. Excessivo para equipe interna de 5–10 pessoas.
- **Apenas mínimo de 8, sem nenhum validador:** deixa "aaaaaaaa" e "password" passarem. `CommonPasswordValidator` cobre esse caso sem fricção para senhas normais.

### Justificativa

Política de senha deve equilibrar segurança com adoção. Para uma equipe interna que conhece o sistema, 8 caracteres + bloqueio de senhas óbvias é suficiente e não gera resistência. Se o sistema for exposto publicamente (Fase 6), a política pode ser revisada novamente.

### Consequências

- `AUTH_PASSWORD_VALIDATORS` em `base.py` contém apenas `MinimumLengthValidator` (min 8) e `CommonPasswordValidator`.
- Django Admin e views de autenticação respeitam automaticamente esses validadores.
- Nenhuma exigência de complexidade é mostrada ao usuário no formulário de senha.

---

## ADR 0026 — Anotação de credenciais de desenvolvimento permanece no `.env` local

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

Auditoria de fundação identificou que o `.env` local (não versionado, gitignored) contém — além das variáveis de ambiente — uma tabela de senhas em texto plano no rodapé: senha do superuser PostgreSQL local, senha do app user PostgreSQL local, e senha provisória do superusuário Django. As linhas estão fora do formato `KEY=VALUE` e não são consumidas pelo runtime.

### Decisão

Manter a anotação no `.env`. Pedro (proprietário) optou explicitamente após auditoria, ciente dos vetores de vazamento que o `.gitignore` não cobre.

### Alternativas consideradas

- **Mover para gerenciador de senhas externo (1Password, Bitwarden, KeePass) e remover do `.env`:** recomendação inicial do auditor. Reduz superfície de vazamento por backup automático, screenshot, share de pasta, indexador, ferramentas de IA com acesso ao filesystem.

### Justificativa

Decisão do proprietário, registrada em transparência. Os vetores citados são reais mas considerados aceitáveis no estágio atual (máquina pessoal, sem deploy, sem outros desenvolvedores).

### Consequências

- A senha provisória `mpd123` do superusuário deve ser trocada via `manage.py changepassword`. A nova senha **não** volta para a tabela do `.env`; vive apenas no banco (hash) e no gerenciador de senhas pessoal de Pedro.
- Reavaliar esta ADR caso o sistema ganhe outros desenvolvedores, troque de máquina, ou entre em ambiente compartilhado.

---

## ADR 0027 — Identidade do mandato genérica em `.env.example`

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

`NOME_DO_MANDATO`, `NOME_CURTO_DO_MANDATO`, `SIGLA_MANDATO` e `DEFAULT_FROM_EMAIL` já são externalizados em variáveis de ambiente. Mas `.env.example` (versionado) e `docs/estrutura-do-repositorio.md` traziam os valores reais do mandato atual ("Vereador Pedro Trés", "gabinetepedrotres.com.br") como exemplo. Como o sistema é construído para ser licenciável a outros parlamentares no futuro, exemplo committado com identidade real contradiz o produto.

### Decisão

Substituir os valores de exemplo por placeholders neutros:

```
NOME_DO_MANDATO=Mandato Exemplo
NOME_CURTO_DO_MANDATO=Mandato
SIGLA_MANDATO=MPD
DEFAULT_FROM_EMAIL=mandato@exemplo.com
```

### Justificativa

Quem clonar o repo amanhã (outro mandato, contribuidor, dev em onboarding) deve entender no primeiro arquivo que abre que esses campos são configuráveis. Anchoring em valores reais sugere o contrário.

### Consequências

- `.env` local de Pedro permanece com os valores reais (gitignored).
- Mesma genericização replicada em `docs/estrutura-do-repositorio.md`.
- Templates já consumem via context processor — nenhuma mudança de código de aplicação.

---

## ADR 0028 — `DeduplicacaoCheckView` exige `pessoas.view_pessoa`

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

`pessoas.views.DeduplicacaoCheckView` (rota `/pessoas/api/deduplicar/`) foi entregue na Fase 2 com apenas `LoginRequiredMixin`. Qualquer usuário autenticado — mesmo sem permissão `pessoas.view_pessoa` — pode consultar pessoas por email/telefone/whatsapp e receber nome de exibição, email, telefone, WhatsApp e URL do detalhe. Endpoint de exfiltração de PII para usuários sem direito de leitura.

### Decisão

Adicionar `PermissionRequiredMixin` com `permission_required = "pessoas.view_pessoa"`. Cobrir com testes: (a) usuário sem perm recebe 403; (b) usuário com perm recebe 200; (c) anônimo é redirecionado para login.

### Justificativa

Busca por dado pessoal **é** leitura de pessoa. Não há diferença substantiva entre `/pessoas/?q=foo` e `/pessoas/api/deduplicar/?email=foo` do ponto de vista de PII; o segundo deve respeitar a mesma permissão.

### Consequências

- Os 4 grupos padrão (Administrador, Chefe de Gabinete, Coordenador, Assessor) já têm `view_pessoa` — nenhum perfil em produção é afetado.
- Teste novo em `pessoas/tests.py`.

---

## ADR 0029 — Auditlog registra Pessoa, Entidade, Vínculo e Tag

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

`django-auditlog` foi instalado na Fase 0 mas nenhum model foi registrado. CLAUDE.md §8 documenta: "registros entram por modelo, fase a fase". A Fase 2 introduziu os models que mais demandam auditoria — dados pessoais de cidadãos sob LGPD — sem registrar nenhum deles.

### Decisão

Registrar `Pessoa`, `Entidade`, `Vinculo` e `Tag` no auditlog via `pessoas/apps.py:ready()`. A trilha cobre criação, edição e exclusão (incluindo soft delete via mudança de `ativo`).

### Alternativas consideradas

- **Aguardar Fase 6 (deploy):** trilha de auditoria só vale com histórico desde o início. Auditoria iniciada amanhã não responde "o que aconteceu antes".

### Justificativa

LGPD exige rastreabilidade ("quem viu, quando, alterou o quê") para dados pessoais. Custo do registro é mínimo (5 linhas); benefício de recuperar histórico após fato é altíssimo.

### Consequências

- Tabela `auditlog_logentry` cresce com edits dos 4 models.
- `criado_por` e `atualizado_em` no model continuam — auditlog é além, não substitui.
- Models de demandas (Fase 3) seguem o mesmo padrão.

---

## ADR 0030 — `criar_usuarios_iniciais` exige `DEBUG=True`

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

O comando `accounts.management.commands.criar_usuarios_iniciais` cria dois usuários com senhas fixas em código (`admin12345`, `usuario12345`) e os adiciona aos grupos correspondentes — incluindo o grupo `Administrador` para `admin@mpd.local`. Útil em dev local; risco grande se rodado por engano em produção: vira backdoor com permissões totais.

### Decisão

Comando aborta com `CommandError` quando `settings.DEBUG` for `False`. Semear usuários iniciais em produção é responsabilidade explícita do admin (via Django Admin ou data migration própria).

### Justificativa

`DEBUG=True` é proxy razoável de "ambiente de desenvolvimento". Defesa simples, sem custo. Se houver razão futura para semear em produção (demo, staging), abrir flag explícita ou comando separado em vez de relaxar este.

### Consequências

- Dev: comportamento inalterado.
- Produção: comando falha com mensagem explicativa, sem efeito colateral.
- Teste cobre o aborto quando `DEBUG=False`.

---

## ADR 0031 — Toggle views usam `PermissionRequiredMixin` + `PermissionDenied`

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

`PessoaToggleAtivoView` e `EntidadeToggleAtivoView` usam só `LoginRequiredMixin` e checam permissão **dentro** do método com `messages.error + redirect`. As outras views do mesmo arquivo padronizam `PermissionRequiredMixin` (gera 403 padrão). Resultado: padrão inconsistente; `get_object_or_404` roda antes da checagem (permite enumeração de PKs); experiência de usuário não-autorizado vira "redirect com mensagem" em vez de 403.

### Decisão

Reescrever ambas com:
- `PermissionRequiredMixin` checando a permissão genérica (`change_pessoa` / `change_entidade`) **antes** do `get_object_or_404`.
- Verificação adicional dentro do método (a permissão muda conforme a ação: `pode_desativar_*` ou `pode_reativar_*`) levantando `PermissionDenied` em vez de `messages.error + redirect`.

### Justificativa

Padronização (princípio do menor espanto). Permissão é checada antes do `get_object_or_404` — sem enumeração. 403 padrão em vez de mensagem flash.

### Consequências

- Comportamento para usuário autorizado: inalterado.
- Comportamento para usuário não-autorizado: 403 em vez de redirect com mensagem.
- Testes existentes ajustados.

---

## ADR 0032 — `django-axes` para rate limiting de login (substitui `django-ratelimit`)

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

`django-ratelimit` está em `pyproject.toml` desde Fase 0 mas **não está aplicado** em nenhuma view. Login (`accounts.MPDLoginView`) está sem proteção contra brute force. Sistema lida com dados pessoais sob LGPD; brute force aberto é fraqueza séria mesmo em escala interna.

### Decisão

Adotar `django-axes`. Lockout por (IP + username) após 5 tentativas falhas, cooldown de 30 minutos. Registrar tentativas em DB (visíveis no Django Admin). Remover `django-ratelimit` das dependências.

### Alternativas consideradas

- **Manter `django-ratelimit` e decorar a view:** simples, leve, suficiente para rate limit por IP. Axes oferece lockout por par (IP, username), dashboard nativo, e integra com signals — encaixe natural com Django Auth e com auditlog (ADR 0029).
- **Defesa em profundidade (axes + ratelimit):** ganho marginal, complexidade extra. Axes sozinho cobre.

### Justificativa

- Senhas são fracas-médias (ADR 0023: 8 chars sem complexidade) — proteção contra adivinhação importa.
- Axes registra tentativas em DB — visibilidade auditável alinhada à LGPD.
- Custo: 1 dep, 1 migração, ~5 linhas em settings, 1 backend de autenticação a mais.

### Consequências

- Login com 5 falhas em 30min trava (IP+email) por 30min. Mensagem de erro informa.
- Admin reseta locks manualmente via Django Admin.
- Dependência `django-ratelimit` removida.

---

## ADR 0033 — `SECURE_PROXY_SSL_HEADER` é env-driven, default desligado

**Data:** 2026-05-08
**Status:** Aceito

### Contexto

`config/settings/production.py` configurava `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` incondicionalmente. Footgun clássico do Django: se a aplicação for diretamente alcançável (sem proxy estrito que sanitize/sete a header), qualquer cliente pode mandar `X-Forwarded-Proto: https` e fazer `request.is_secure()` retornar True — bypassando `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, etc. A própria documentação do Django avisa.

### Decisão

Tornar opt-in via env var `DJANGO_TRUST_PROXY_SSL_HEADER`. Default desligado. `.env.example` documenta quando ativar (apenas atrás de proxy estrito — nginx, Caddy, Cloudflare, etc.).

### Justificativa

Default seguro. Ativação consciente. Documentação no próprio exemplo evita armadilha quando o deploy for configurado por alguém que não conhece o histórico desta decisão.

### Consequências

- Sem deploy hoje: nenhum efeito prático.
- Quando deploy chegar: quem fizer setup decide explicitamente se confia na header. Decisão fica documentada via env var no servidor.

---

## ADR 0034 — Remoção das preferências de comunicação em massa (supersede ADR 0012)

**Data:** 2026-05-09
**Status:** Aceito (supersede ADR 0012)

### Contexto

ADR 0012 introduziu 4 booleans em `Pessoa` (`nao_telefonar`, `nao_enviar_email`, `nao_enviar_sms`, `nao_compartilhar_dados`) inspirados no CiviCRM, com o argumento de "preparar para newsletter da v1.x". O MVP, porém, não tem disparo em massa nem está no escopo das próximas fases — as flags não impedem nada hoje, e ocupam espaço cognitivo no formulário e no detalhe da pessoa.

Pedro questionou o valor de manter campos que "não servem de nada" no sistema atual.

### Decisão

Remover as 4 flags do model `Pessoa`, do form, do admin, dos templates e dos docs. Reintroduzir quando (e se) o disparo em massa entrar no produto — cada uma volta com semântica clara, validada na implementação concreta.

### Justificativa

- **YAGNI:** schema deve refletir capacidades atuais. Campo que não tem código que o consulte é ruído.
- **UX:** 4 checkboxes sem efeito hoje confundem quem cadastra. Pior que ausência.
- **Custo de readicionar é trivial:** uma migration, um campo por vez, com a regra real codificada na hora.
- **`nao_compartilhar_dados` foi avaliado separadamente:** apesar de aplicável a casos manuais (indicação a terceiros), Pedro optou por remover também — a prática de compartilhamento manual será governada por orientação de equipe e auditoria de log, não por flag por pessoa.

### Consequências

- Migration drop columns nas 4 colunas; LGPD permanece coberta via auditlog (ADR 0029).
- ADR 0012 fica registrada como histórico, supersedida.
- Anonimização (`Pessoa.anonimizar()`) deixa de zerar essas flags.
- Quando newsletter entrar no roadmap (v1.x), nova ADR específica decide quais flags retornam e como.

---

## ADR 0035 — Números de telefone como entidade própria, com tipo

**Data:** 2026-05-09
**Status:** Aceito

### Contexto

O design original tinha dois campos diretos em `Pessoa`: `telefone` e `whatsapp`. Pedro identificou na verificação manual que isso confunde categorias diferentes: **número de telefone é dado**, **canal de comunicação é tipo**. Pessoa pode ter mais de um número, e cada número tem natureza própria (celular, fixo) e capacidade de WhatsApp. A analogia da agenda do celular foi explícita: cadastra-se um número e marca-se o que ele é.

### Decisão

Substituir os campos `telefone` e `whatsapp` por um modelo `Telefone` em relação 1:N com `Pessoa`:

```
Telefone
  ├── pessoa (FK → Pessoa, CASCADE)
  ├── numero (10 ou 11 dígitos, normalizado)
  ├── tipo ("celular" | "fixo")
  ├── eh_whatsapp (boolean; só vale com tipo=celular)
  ├── rotulo (opcional — "trabalho", "recado", etc.)
  └── criado_em
```

**Validação por tipo:**
- `celular`: exatamente 11 dígitos, com `9` na primeira posição após DDD (regra Anatel para móveis).
- `fixo`: exatamente 10 dígitos.
- `eh_whatsapp=True` exige `tipo=celular`.

A regra "pelo menos um meio de contato" passa a ser: `email` preenchido **ou** ao menos um `Telefone` cadastrado. Validada na view (precisa do formset processado) — não no `clean()` do model.

### Alternativas consideradas

- **Manter `telefone` e `whatsapp` como campos diretos:** simples, mas mistura dado com canal e impede múltiplos números por pessoa.
- **Um campo `telefone` + boolean `eh_whatsapp`:** ergonômico para o caso comum (mesmo número), mas exclui o cenário real de WhatsApp Business em número diferente do celular pessoal.

### Justificativa

- Modelo reflete a realidade: número é dado, canal é tipo.
- Cobre múltiplos números por pessoa sem reabrir o esquema depois (cenário comum: celular pessoal + recado da família + comercial).
- Validação por tipo elimina entrada de número sem DDD.
- Formatação para exibição vira propriedade derivada (`numero_formatado`), não estado.

### Consequências

- **Schema reescrito (não migrado):** Fase 2 ainda em verificação manual; migration `0001` é editada para já nascer com a estrutura nova. Migration `0003_remover_preferencias_comunicacao` (drop das flags LGPD) é absorvida na nova `0001` e deletada. Banco de dev é resetado (`migrate pessoas zero && migrate`). Ver memory `feedback_refazer_vs_migrar.md`.
- Form de Pessoa passa a ter formset inline de telefones (adicionar/remover linhas via JS).
- Detalhe lista os números formatados com badge de tipo e ícone de WhatsApp.
- Lista mostra o primeiro telefone disponível (preferência: celular com WhatsApp).
- Deduplicação busca em `Telefone` ao invés de `Pessoa.telefone`/`whatsapp`.
- Auditlog registra `Telefone` (LGPD, mesmo motivo de ADR 0029).
- Doc `modelo-de-dados.md` atualizado: `Pessoa` perde `telefone` e `whatsapp`; nova tabela `pessoas_telefone`.

---

## ADR 0036 — Geocodificação de endereços de Pessoa e Entidade (programado para v2.x)

**Data:** 2026-05-09
**Status:** Aceito — implementação programada para v2.x (pós-MVP)

### Contexto

`Pessoa` e `Entidade` têm endereço estruturado (logradouro, número, bairro, cidade, UF, CEP), mas hoje só como texto. Para um mandato municipal, a dimensão territorial é estratégica: identificar concentrações de demandas por bairro/região, mapear base de relacionamento, cruzar com microrregiões eleitorais, validar plausibilidade do endereço (CEP de Recife com cidade declarada como Olinda, por exemplo), e habilitar mapas/heatmaps em dashboards.

Nada disso é viável sem coordenadas (lat/long). Texto de endereço não permite agregação espacial, distância, raio de busca, ou visualização cartográfica.

A decisão hoje é **registrar o compromisso**, não implementar agora — o MVP entrega o relacionamento básico, e geocodificação fora de hora vira complexidade prematura (escolha de provedor, signals, retry, fallback, custo).

### Decisão

**Adicionar geocodificação no v2.x**, no mesmo ciclo de **multi-endereço por cidadão** (já listado em `roadmap.md` §5 v2.x). Multi-endereço sem geocodificação é desperdício; geocodificação sem multi-endereço cobre só metade do uso real.

**Escopo proposto para v2.x:**
- `Pessoa` e `Entidade` (e o futuro modelo de endereço múltiplo) ganham `latitude` e `longitude` (`DecimalField`, nulláveis), `geocodificado_em` (timestamp) e `geocodificacao_status` (`pendente | sucesso | falha | manual`).
- Geocodificação acionada por signal `post_save` quando os campos de endereço mudam, executada **assíncrona** (Celery ou `django-q2` — decisão de provider de fila fica para a ADR de implementação).
- Comando de management `geocodificar_pendentes` para backfill e re-tentativa de falhas.
- Possibilidade de override manual (operador ajusta lat/long quando o provedor erra) — daí o status `manual`, que o signal não sobrescreve.

**Provedor primário proposto: Nominatim (OpenStreetMap)** — gratuito, sem chave, sem custo recorrente. Aceita `User-Agent` identificável e respeita 1 req/s. Cobertura de Brasil é aceitável para municípios médios e capitais; cai em zona rural e endereços incompletos.

**Fallback opcional configurável via env: Google Geocoding API** — chamado apenas para endereços com `geocodificacao_status=falha` após N tentativas no Nominatim. Permite ao mandato escolher entre custo zero (só Nominatim) ou cobertura quase total (paga ~US$ 5/1.000 reqs no fallback).

A escolha definitiva de provedor — e se o fallback será ativado — é decisão da ADR de implementação no v2.x, com base em volume real de cadastros e disponibilidade de orçamento.

### Alternativas consideradas

- **Implementar agora (na Fase 2/3):** descartado. Não há tela de mapa, dashboard territorial, nem multi-endereço para justificar — coordenadas ficariam guardadas sem consumidor. Viola "produto sobre técnica" e YAGNI.
- **Geocodificação on-demand (apenas quando uma tela pedir):** descartado. Adiciona latência imprevisível à navegação e não cobre análises em lote (heatmap precisa de tudo geocodificado de antemão).
- **Provedor único Google desde o início:** descartado como default. Custo recorrente injustificado para um mandato municipal cujo volume cabe na cota gratuita do Nominatim. Fica como opção via env.
- **Provedor único Nominatim, sem fallback:** descartado. Endereços rurais e periferias têm taxa de falha relevante; sem fallback, o mandato fica cego nessa fatia.
- **Cálculo de coordenadas a partir do CEP via base do IBGE/Correios:** descartado. CEP brasileiro é genérico (uma rua inteira pode ter um único CEP); precisão ao nível de quarteirão exige geocodificador real.

### Consequências

- **Schema (v2.x):** novos campos `latitude`, `longitude`, `geocodificado_em`, `geocodificacao_status` no modelo de endereço (provavelmente um novo `Endereco` quando multi-endereço entrar; senão, em `Pessoa` e `Entidade` diretamente).
- **Dependências novas:** biblioteca cliente HTTP já existente (`httpx` ou `requests`); fila assíncrona (`django-q2` é o candidato simples — decisão de implementação). Não exige PostGIS no MVP do v2.x: `DecimalField` e cálculo Haversine em Python cobrem distância. PostGIS vira ADR separada se análise espacial complexa surgir.
- **LGPD:** coordenadas são representação transformada do endereço (já consentido no cadastro), não criam categoria nova de dado. Mas habilitam análise em massa que texto não permitia. Auditlog já cobre `Pessoa` e `Entidade` (ADR 0029); ao virar campo persistido, a alteração entra no log automaticamente. Política de retenção segue a do registro principal (anonimização zera lat/long junto).
- **Falha do provedor:** sistema funciona com `latitude=NULL`. Telas que dependem de mapa filtram o que está geocodificado; cadastro nunca é bloqueado por falha de geocodificador.
- **Custo zero por padrão:** Nominatim é gratuito. Mandato só paga se ativar Google explicitamente.
- **Dependência externa:** Nominatim pode ficar fora do ar ou mudar políticas. Aceitável: campo é nulável e o backfill pode rodar a qualquer momento depois.

### Aberto para a ADR de implementação (v2.x)

- Provedor de fila assíncrona (`django-q2` vs Celery vs RQ).
- Política de re-tentativa (quantas vezes? backoff?).
- Cache de respostas (mesmo endereço cadastrado duas vezes → uma chamada só).
- Tela de revisão para endereços com baixa confiança.

---

## ADR 0037 — Contatos como entidades plurais (Email e RedeSocial), agrupados sob "Contatos"

**Data:** 2026-05-09
**Status:** Aceito

### Contexto

Após reorganizar telefones em entidade própria (ADR 0035), Pedro identificou na verificação manual que email e instagram permaneciam como campos diretos em `Pessoa` — quebrando a coerência. Pessoa pode ter múltiplos emails (pessoal, trabalho), e a presença em redes sociais raramente se limita ao Instagram (Facebook, LinkedIn, X são canais frequentes em mandato municipal). Tratar email como campo único e instagram como o único canal de rede social nomeado distorce a realidade.

### Decisão

Aplicar o mesmo padrão de Telefone aos demais canais. Pessoa passa a ter três coleções 1:N:

```
Pessoa
  ├── telefones    (já existente — ADR 0035)
  ├── emails       (NOVO: EmailPessoa)
  └── redes_sociais (NOVO: RedeSocial)
```

Campos `Pessoa.email` e `Pessoa.instagram` são removidos.

**`EmailPessoa`:** `endereco` (EmailField, validação nativa), `rotulo` opcional (livre).
**`RedeSocial`:** `plataforma` (enum: `instagram`, `facebook`, `linkedin`, `x_twitter`, `outro`), `valor` (handle ou URL), `rotulo` opcional (especialmente útil quando `plataforma=outro` para indicar qual rede).

**Regra de canal mínimo:** pelo menos 1 telefone OU 1 email OU 1 rede social. Validada na view (depende dos formsets processados).

**UI:** uma seção única "Contatos" no formulário, com três sub-blocos (Telefones, E-mails, Redes sociais) — cada um com lista + botão "+ adicionar". Mesma mecânica de formset inline.

### Alternativas consideradas

- **Tabela única `CanalContato` polimórfica** (telefone, email e rede social na mesma tabela com tipo + valor): unifica modelo mas perde validação específica (email tem `@`, celular tem 11 dígitos com 9). Descartado em favor de clareza e validação por tipo.
- **Manter email/instagram diretos:** simples, mas inconsistente — alguns canais como entidades, outros como campo. UX confusa ("por que telefone tem múltiplos e email não?").
- **Plataforma como texto livre em vez de enum:** flexível mas degrada análise (mesmo Instagram cadastrado como "Instagram", "instagram", "IG"). Enum + opção "Outro" com rótulo livre cobre os dois cenários.

### Justificativa

- Coerência interna: três canais, três entidades, mesma mecânica.
- Realidade do mandato: pessoas têm presença em múltiplas redes; ter só Instagram como campo nomeado é viés.
- Custo de adicionar agora é baixo (fase ainda não tagueada — migration 0001 é editada, sem migration de drop).

### Consequências

- Drop dos campos `email` e `instagram` em `Pessoa`. Schema reescrito na 0001 (sem migration de remoção).
- 3 novos models registrados em `auditlog` (LGPD, mesmo motivo de ADR 0029).
- Form de Pessoa ganha 2 novos formsets além do de Telefone.
- View processa 3 formsets e valida "ao menos 1 canal".
- Deduplicação busca em telefones, emails e redes sociais.
- Admin tem inlines para os 3 canais.
- Lista mostra primeiro email + primeiro telefone (ou primeira rede social, se nada mais).
- Anonimização (LGPD) deleta os 3 conjuntos em cascade.

---

## ADR 0038 — `slug_publico` em URLs públicas (mantém ADR 0025; resolve ADR 0002)

**Data:** 2026-05-09
**Status:** Aceito (não supersede ADR 0025; soma uma camada de slug a ela)

### Contexto

ADR 0025 padronizou `BigAutoField` como PK em todos os models. Pedro questionou na verificação manual: a primeira pessoa cadastrada gerou URL `/pessoas/1/`, expondo volume da base e ordem de cadastro — exatamente o cenário que ADR 0002 (UUID universal) buscava evitar.

O problema real era a **URL pública**, não a PK em si. Trocar PK por UUID resolveria, mas ao custo de URLs de 36 caracteres, índice de PK 2x maior, e fricção em integrações que esperam PK numérica (admin, FKs, formulários, auditlog). Existe alternativa mais barata: manter `BigAutoField` como PK interna e adicionar um identificador público separado.

### Decisão

**`BigAutoField` continua sendo a PK de todos os models do MVP** (mantém ADR 0025 sem alteração).

**Adicionar campo `slug_publico` em models cuja URL aparece para o usuário final:**

- `slug_publico = models.CharField(max_length=12, unique=True, blank=True, editable=False)`.
- Gerado em `pre_save` via `uuid.uuid4().hex[:12]` (12 caracteres hexadecimais), com retry em colisão.
- Aplicado em `Pessoa` e `Entidade` na Fase 2; aplicar nos models de Fase 3+ que ganharem URL pública (`Demanda` etc.).
- **Não** aplicar em models internos ao fluxo (`Telefone`, `EmailPessoa`, `RedeSocial`, `Vinculo`, `Tag`) que não têm rota pública dedicada.

**URLs públicas usam `slug_publico`:**

- `/pessoas/<slug>/`, `/pessoas/<slug>/editar/`, `/entidades/<slug>/`.
- Views resolvem por `slug_field = "slug_publico"` (`DetailView`/`UpdateView`) ou `get_object_or_404(Pessoa, slug_publico=slug)` (views `View`).

### Alternativas consideradas

- **`UUIDField` como PK (proposta inicial desta ADR):** atinge o mesmo objetivo de não vazar volume, mas: URL 3x mais longa (36 chars vs 12), índice de PK 2x maior (16 bytes vs 8), fricção com auditlog/admin/forms que esperam PK numérica, FKs maiores em todas as tabelas relacionadas. O ganho marginal sobre slug separado não compensa.
- **Slug textual (ex.: `nome-sobrenome`):** legível, mas vaza identidade. Inaceitável para PII.
- **Hash mais longo (ex.: 16 chars):** desnecessário para a escala (12 chars hex = 281 trilhões de combinações; colisão antes do mandato encerrar é improvável).

### Justificativa

- **Mantém o pipeline padrão Django** (BigAutoField, FKs numéricas, admin natural).
- **URL pública não revela volume**: `/pessoas/a3f9b1c4d2e5/` não conta nada sobre quantas pessoas existem.
- **URLs curtas**: 12 chars cabem em SMS, e-mails, anotações, sem quebrar layouts.
- **Migração interna invisível**: caso o slug precise crescer (16 chars no futuro), é alteração isolada — PKs e FKs internas não são afetadas.

### Consequências

- `Pessoa` e `Entidade` têm `slug_publico` (12 chars hex), gerado por `pessoas/signals.py` no `pre_save` antes do primeiro save.
- URLs em [pessoas/urls.py](../pessoas/urls.py) usam `<slug:slug>` em vez de `<int:pk>`.
- ADR 0002 (UUID universal) fica registrada como ideia inicial, mas a abordagem que vigora é `BigAutoField` + slug separado, conforme esta ADR e ADR 0025.
- Fase 3 deve aplicar o mesmo padrão a `Demanda` (a primeira coisa que será compartilhada via URL).

---

## ADR 0039 — Drop do campo `categoria` em Tag (supersede ADR 0005 parcialmente; revisita ADR 0006)

**Data:** 2026-05-09
**Status:** Aceito

### Contexto

ADR 0005 introduziu Tag como tabela única com campo `categoria` (`tema`/`perfil`/`territorio`/`livre`) — argumento principal: unificar curadoria entre Pessoa, Entidade, Demanda. ADR 0006 acrescentou que **o tema da Demanda é uma tag de categoria `tema`**, criando o único uso estrutural real desse campo.

Na verificação manual da Fase 2, Pedro questionou a razão de ser das categorias. Conclusão honesta: dos 4 valores existentes, apenas `tema` carrega comportamento codificado (Fase 3); os outros 3 (`perfil`, `territorio`, `livre`) são só rótulo visual sem efeito no sistema. O custo cognitivo (dropdown obrigatório no cadastro de tag, refactor pra editar a lista, mais um eixo de filtragem) não se paga.

Pedro descreveu o uso real que ele enxerga: tags servem para "agrupar pessoas que não fazem parte da mesma entidade mas têm interesses em comum, ou compartilham uma origem (estudaram na mesma escola, na mesma faculdade)" — **forma fluida e dinâmica de agrupar pessoas sem enrijecer o cadastro**. Esse mental model é incompatível com categorização hierárquica fixa.

### Decisão

Remover o campo `categoria` de `Tag`. Tag passa a ter apenas `nome`, `cor`, `descricao`, `ativo`, `criado_em`. Sem hierarquia, sem dropdown, sem agrupamento conceitual.

ADR 0005 fica supersedida no que toca à categoria; o argumento "tabela única e compartilhada" continua valendo.

ADR 0006 ("tema da demanda é uma tag") **continua válida em essência** — mas o critério de "qual tag pode ser tema" será redefinido na implementação da Fase 3. Opções a serem decididas na ADR de implementação da Demanda:

- (a) qualquer tag pode ser tema — Demanda tem M:N para Tag, sem distinção;
- (b) flag `usar_como_tema_de_demanda` em Tag — explícito, sem categoria;
- (c) modelo `Tema` separado — mais rígido, descartável.

Decidir quando a Demanda existir, com caso de uso real à mão.

### Alternativas consideradas

- **Reduzir para 2 categorias** (`tema` e `outro`): meio caminho, ainda paga preço por pouco ganho.
- **Tornar categorias editáveis via modelo `CategoriaTag`**: adiciona complexidade pra resolver problema que não é real (curadoria visual de tags).
- **Manter como está**: Pedro se convenceu de que enrijece o uso pretendido (tags como agrupamentos fluídos).

### Justificativa

- Sistemas comparáveis (GitHub labels, Linear, Notion tags, Trello) usam tags lisas.
- Mental model do produto é "etiquetar livremente", não "classificar em famílias".
- Refactor pra reintroduzir categorização (se algum dia precisar) é barato — adicionar coluna numa única tabela, com dados existentes preservados.

### Consequências

- `Tag.categoria` removido. Choices `CATEGORIA_*` removidas do model.
- Form de tag perde o select de categoria.
- Admin perde `list_filter` por categoria.
- Lista `/configuracoes/tags/` perde a coluna categoria.
- Filtro de tags na lista de pessoas continua igual (filtra pelo nome/id da tag).
- Tag passa a ordenar por `nome`.
- Schema reescrito na migration 0001 (Fase 2 ainda não tagueada — ver memory `feedback_refazer_vs_migrar.md`).
- Pra Fase 3, ADR de Demanda decide critério de "tag pode ser tema" entre as opções (a/b/c).

---

## ADR 0040 — Bloqueio de auto-edição de `is_staff` (mitigação tática até DT-011)

**Data:** 2026-05-09
**Status:** Aceito (provisório — solução completa registrada em DT-011)

### Contexto

Auditoria pré-PR identificou que o app `accounts` ficou para trás na migração para Django Groups (que aconteceu no app `pessoas` na Fase 2 — ADR 0024). `StaffRequiredMixin` ainda gata todas as views de gestão de usuários em `is_staff`, e `UsuarioCreateForm`/`UsuarioUpdateForm` expõem `is_staff` como campo editável. Resultado: qualquer staff promove qualquer outro staff via formulário, e — pior — pode editar a própria flag (rebaixando-se por engano e perdendo acesso, ou subindo um ex-staff de volta).

A solução completa (mover gestão de usuários para `PermissionRequiredMixin` + permissão customizada `accounts.gerenciar_usuarios` no grupo Administrador) é trabalho arquitetural não-trivial. Está registrada em DT-011.

### Decisão

**Mitigação tática agora**, sem refactor arquitetural:

- `UsuarioUpdateView.form_valid` rejeita qualquer mudança em `is_staff` quando o usuário sendo editado é o próprio usuário logado.
- `UsuarioToggleAtivoView` já bloqueia self-deactivation (existente desde Fase 1).
- A combinação fecha o pior cenário (admin se rebaixa por engano e fica sem acesso) e mantém o resto funcionando.

### Alternativas consideradas

- **Resolver tudo agora (refactor para Groups):** trabalho considerável; melhor consolidar com a próxima refactor planejada (Fase 3 ou pré-produção). Documentado em DT-011.
- **Não fazer nada e só registrar DT-011:** o auto-rebaixamento é caso de "pé na própria mão" que custa 10 linhas evitar. Vale.

### Justificativa

- Custo da mitigação: 10–15 linhas + teste.
- Fecha o cenário concreto que tem maior probabilidade de acontecer no dia-a-dia (rebaixamento acidental).
- Não atrapalha refactor futuro: quando DT-011 for endereçado, a checagem some junto com `StaffRequiredMixin`.

### Consequências

- Editar usuário via UI: tudo igual, exceto que o checkbox `is_staff` para o próprio usuário, se mudado, é silenciosamente revertido com mensagem de erro.
- Privilege creep entre admins (admin A promove admin B) continua possível — fix arquitetural cobre. DT-011.

---

## ADR 0041 — Coordenação como atributo do Usuário

**Data:** 2026-05-10
**Status:** Aceito

### Contexto

A Fase 3 introduz `Demanda.coordenacao_responsavel` (`gabinete | juridico | comunicacao`) e regras de visibilidade que dependem dela: Coordenador (CO) só pode editar demandas da própria coordenação; Assessor (AS) de outra coordenação não vê demandas restritas a menos que seja o responsável. `permissoes.md` §3.3 codifica esse comportamento.

Para que essas regras sejam aplicáveis no código, é preciso saber qual a coordenação de cada usuário. O modelo atual `accounts.Usuario` tem `cargo` (texto livre, não estruturado) — insuficiente para checagem programática.

### Decisão

Adicionar campo `coordenacao` em `Usuario`:

- `CharField(max_length=15, blank=True, default="")` com choices `gabinete | juridico | comunicacao`.
- Vazio significa "não atribuído a coordenação" (admins, superusers, ou usuários inativos).
- Exposto em `UsuarioCreateForm`, `UsuarioUpdateForm` e Django Admin.

### Alternativas consideradas

- **Inferir coordenação por grupo Django:** criar grupos por coordenação (ex: `Coordenador-Juridico`). Rejeitado: mistura permissão (o que pode fazer) com escopo (de qual time). Grupo já carrega o perfil (CO, AS); somar coordenação ao nome do grupo cria explosão combinatória.
- **Tabela separada `MembroCoordenacao`:** overhead. Coordenação é atributo singular do usuário (cada usuário pertence a no máximo uma).
- **Adiar até Fase 4 simplificando regras:** rejeitado. As regras de coordenação fazem parte do critério de aceite da Fase 3 (referência a `permissoes.md` §3.3 no roadmap §4.3.2).

### Justificativa

- Usuário pertence a uma coordenação singular — atributo direto é o modelado correto.
- `cargo` continua existindo para texto livre, separado de `coordenacao` (estrutural).
- Permite query direta: `Demanda.objects.filter(coordenacao_responsavel=user.coordenacao)`.

### Consequências

- Migration `accounts/0004_adicionar_coordenacao` adiciona coluna nullable — usuários existentes não são afetados.
- `permissoes.md` referencia `user.coordenacao` para checks de visibilidade.
- Mudança de coordenação de um usuário não desvincula das demandas atribuídas (assessor pode trocar de time mantendo demandas em transição).

---

## ADR 0042 — Tema separado de Tag (supersede parcialmente ADR 0039)

**Data:** 2026-05-10
**Status:** Aceito

### Contexto

ADR 0039 estabeleceu Tag plana (sem categoria), compartilhada por Pessoa, Entidade e Demanda. A decisão era ergonômica para Fase 2 — naquela fase, só Pessoa e Entidade usavam Tag, e a separação por categoria ficava abstrata.

A Fase 3 (Demanda) revelou um conflito empírico que a ADR 0039 não previu:

| Tag de Pessoa/Entidade | Tag de Demanda |
|---|---|
| Caracteriza *quem é* (líder local, gestante, microempresa) | Caracteriza *do que se trata* (Saúde, Educação, Mobilidade) |
| Filtro útil: "líderes locais do bairro X" | Filtro útil: "demandas de saúde no bairro X" |
| Não faz sentido filtrar Pessoa por "Saúde" | Não faz sentido filtrar Demanda por "Líder local" |

Pool único cria ruído: o seletor de tags em Demanda mistura "Líder local" e "Microempresa" com "Saúde"; o seletor em Pessoa mistura "Mobilidade urbana" com "Gestante". Em escala (50+ tags em 6 meses de uso real), vira dívida cognitiva.

### Decisão

Criar modelo `Tema` em `demandas/`, distinto de `pessoas.Tag`:

- `Tema` tem nome, cor, descricao, ativo (estrutura simples, similar a Tag).
- `Demanda.temas` substitui `Demanda.tags` (M:N para `demandas.Tema`).
- `Pessoa.tags` e `Entidade.tags` continuam apontando para `pessoas.Tag` (sem alteração).
- CRUD de Tema em `/demandas/temas/`, com paleta de cores fixas e fluxo de arquivar (mesma UX de Tag).
- Permissões: ADM/CG/CO criam/editam tema; AS apenas atribui em demanda.
- Auditlog registra Tema.

### Alternativas consideradas e descartadas

- **Reintroduzir `Tag.categoria` com 2 valores (`caracteristica` | `tema`):** restritivo demais. Pessoa pode legitimamente ter tag temática (Maria atua na pauta de Saúde), e categoria binária impede.
- **3 booleans em Tag (`aplica_a_pessoa`, `aplica_a_entidade`, `aplica_a_demanda`):** flexível, mas Pedro avaliou como "difícil de gerir" — exige decisão fine-grained na criação de cada tag.
- **Manter pool único e disciplinar pela equipe:** sem barreira técnica, vira dívida em escala.

### Justificativa

- **Domínios separados.** Caracterização de pessoa/entidade ≠ categorização de demanda. Modelos separados refletem a separação conceitual real.
- **Gestão simplificada.** Quem administra temas (CG/CO) não polui o vocabulário de tags de pessoa, e vice-versa.
- **Painel de análise (Fase 5) fica limpo.** "Demandas por tema" usa `Demanda.temas`; "Pessoas por característica" usa `Pessoa.tags`. Sem necessidade de filtro por categoria nas queries.
- **Refactor barato.** Tema reaproveita 100% da UX de Tag (paleta de cores, archive flow, badges visuais com color-mix). É um modelo novo com lista/form/admin clonados.

### Consequências

- Migration `demandas/0003_separar_tema_de_tag` remove `Demanda.tags`, cria `Tema`, adiciona `Demanda.temas`. Como Fase 3 acabou de subir e ainda não tem dados em produção, não há perda real (seed é refeito).
- Permissões `view_tema/add_tema/change_tema/delete_tema` adicionadas aos grupos via `0004_grupos_padrao_tema`.
- `criar_dados_teste` cria 5 temas exemplo (Mobilidade urbana, Saúde, Educação, Cultura, Infraestrutura) e atribui nas demandas seedadas.
- Templates de Demanda (lista, detalhe, form) referenciam temas em vez de tags.
- Link "Temas" no menu superior, ao lado de "Tags" — torna a separação visível para o usuário.
- ADR 0039 continua valendo no domínio de Pessoa/Entidade (Tag plana, sem categoria).

---

*Decisões adicionadas em ordem cronológica conforme surgem. Cada decisão registrada uma vez; alterações futuras criam nova ADR (não editam a anterior).*
