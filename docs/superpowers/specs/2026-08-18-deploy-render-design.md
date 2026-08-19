# Deploy do MPD no Render — Design

**Data:** 2026-08-18
**Fase:** 7 (Polimento e Web) — trilha de infraestrutura
**Status:** aprovado por Pedro em 2026-08-18, pendente de plano de implementação
**Branch:** `feature/deploy-render`

---

## 1. Objetivo

Colocar o MPD no ar em `render.com` como **produção real**: equipe do gabinete usando com dados reais de cidadãos, três níveis de permissão (Administrador, Chefe de Gabinete, Assessor), anexos que sobrevivem a atualizações do sistema e backup confiável.

O deploy é executado por **Pedro, que nunca fez deploy de nenhum sistema**. Isso não é um detalhe de contexto — é um requisito de design. Cada escolha abaixo privilegia menos peças móveis e mensagens de erro diagnosticáveis sobre elegância ou completude arquitetural.

## 2. Decisões de produto (tomadas por Pedro em 2026-08-18)

| Decisão | Escolha | Consequência |
|---|---|---|
| Natureza do ambiente | Produção real, plano pago | Banco free expira em 30 dias e leva os dados — inviável. Backup e persistência de anexos viram obrigatórios |
| Endereço | `<nome>.onrender.com` | Sem custo de domínio nem DNS. Configuração fica parametrizada por env var para trocar depois sem mexer em código |
| Recuperação de senha | Manual pelo Admin, e-mail no backlog | Nenhum serviço de e-mail a configurar. Item registrado no backlog |
| Empacotamento | Blueprint (`render.yaml`), Python nativo | Diverge do roadmap §4.6.2 item 4, que pedia Docker. Registrado em ADR |

## 3. Arquitetura no Render

Três recursos, declarados em `render.yaml` e criados de uma vez via **New Blueprint** no painel:

| Recurso | Plano | Custo aprox./mês | Papel |
|---|---|---|---|
| Web Service (Python) | Starter | US$ 7 | Roda Django sob gunicorn. Health check em `/healthz/` (rota já existente; a barra final importa — sem ela o Django responde 301) |
| PostgreSQL | Basic-256mb | US$ 6 | Banco. Point-in-time recovery de 3 dias (workspace Hobby) |
| Persistent Disk | 1 GB | US$ 0,25 | Montado em `/var/data/media`; recebe `MEDIA_ROOT`. Snapshot diário automático, retenção ≥7 dias |

**Total: ~US$ 13,25/mês**, antes de crescimento de banda/armazenamento.

### 3.1. Por que disco persistente e não object storage

O sistema de arquivos de um Web Service do Render é efêmero: tudo fora do ponto de montagem do disco é apagado a cada deploy ou restart. [demandas/models.py](../../../demandas/models.py) grava anexos via `FileField` com `upload_to="anexos/%Y/%m/"` em `FileSystemStorage`. Sem disco persistente, **todo anexo enviado pela equipe desaparece na próxima atualização do sistema.**

Duas soluções possíveis:

1. **Disco persistente do Render** (escolhida) — muda uma variável de ambiente. Zero dependência nova, zero conta em terceiro, snapshot diário incluso.
2. **Object storage externo** (Cloudflare R2 / S3 + `django-storages`) — remove as limitações do disco, ao custo de mais uma conta para administrar, mais uma biblioteca no projeto e credenciais adicionais para gerenciar.

**Trade-off aceito:** um disco anexado impede *zero-downtime deploys* (o Render para a instância atual antes de subir a nova) e impede escala horizontal. Na prática: **~1 minuto de indisponibilidade a cada atualização**, e o sistema roda sempre numa máquina só. Para um gabinete municipal com equipe de meia dúzia de pessoas, nenhum dos dois pesa. Se um dia pesar, a migração para R2 é localizada (troca de `STORAGES["default"]`), sem tocar em models nem views.

### 3.2. Por que os anexos não precisam de rota pública

[demandas/views/anexos.py](../../../demandas/views/anexos.py) serve anexos por `AnexoDownloadView` com `FileResponse` e checagem de permissão por objeto — nunca por URL direta de `MEDIA_URL`. Consequência de design: **nada em `/var/data/media` é alcançável sem passar pela camada de permissão do Django.** Arquivo com dado pessoal de cidadão não fica exposto na internet, e não é preciso configurar o servidor para servir `MEDIA_URL` em produção.

## 4. Mudanças no repositório

Nenhuma mudança em `models.py`, `views.py`, templates ou testes. A suíte de **239 testes** (linha de base verificada em 2026-08-18; o `CLAUDE.md` ainda registra 235, defasado desde o realinhamento da matriz de permissões) permanece intacta e é gate de cada etapa.

### 4.1. Arquivos novos

**`render.yaml`** — Blueprint declarando os três recursos, as variáveis de ambiente (com `generateValue: true` para `DJANGO_SECRET_KEY`, `fromDatabase` para `DATABASE_URL`), o ponto de montagem do disco e `healthCheckPath: /healthz/`.

**`build.sh`** (executável) — comando de build:

1. `uv sync --frozen --no-dev` — instala dependências a partir do `uv.lock`
2. Baixa o binário `tailwindcss-linux-x64` do release oficial e compila `static/css/tailwind-input.css` → `static/css/tailwind-output.css --minify`
3. `uv run python manage.py collectstatic --no-input`

**`.python-version`** — fixa `3.12`, em paridade com o ambiente local (Python 3.12.10). Sem esse arquivo o Render usaria 3.14.3 por padrão, que não é a versão em que a suíte roda.

**Nome do serviço:** `mpd`, resultando em `mpd.onrender.com` — sujeito a disponibilidade no momento da criação, já que o subdomínio é global no Render. Se estiver tomado, Pedro escolhe uma variante na hora; o nome entra em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` por variável de ambiente, sem alteração de código.

### 4.2. O passo do Tailwind (achado da investigação)

[templates/base.html:10](../../../templates/base.html#L10) carrega `css/tailwind-output.css`, e esse arquivo está no `.gitignore` — é gerado localmente por um binário que cada desenvolvedor baixa ([README.md:64](../../../README.md#L64)). **Subir o repositório sem compilar o CSS coloca o MPD no ar sem estilo algum**: HTML cru, sem layout.

O `build.sh` replica exatamente o procedimento já documentado no README, só que para Linux. Se o download do binário falhar, o build falha em voz alta e o Render mantém a versão anterior no ar — falha ruidosa é preferível a um site publicado sem CSS.

**Alternativa descartada:** versionar `tailwind-output.css`. Evitaria dependência de rede no build, mas cria um passo manual esquecível (recompilar e commitar a cada mudança de template), cujo sintoma é CSS silenciosamente desatualizado em produção.

### 4.3. `pyproject.toml`

Acrescenta `gunicorn` às dependências de produção. O `runserver` do Django é ferramenta de desenvolvimento e não deve atender tráfego real.

### 4.4. `config/settings/production.py`

Quatro ajustes:

1. **`MEDIA_ROOT`** — aponta para o ponto de montagem do disco, via env var (default preservado para não quebrar ambiente local).
2. **`CSRF_TRUSTED_ORIGINS`** — lido de env var. Necessário para POSTs sob HTTPS atrás do proxy do Render.
3. **Logging para `stdout`** — o Render captura a saída padrão como log do serviço. Sem isso, erros de produção ficam invisíveis. Formato estruturado, nível `INFO`, com `django.request` em `ERROR`.
4. **`django-axes` atrás de proxy** — hoje [config/settings/base.py:79-82](../../../config/settings/base.py#L79-L82) configura lockout por `(ip_address, username)`. Atrás do proxy do Render, sem ajuste, **todo acesso aparece vindo do mesmo IP** (o do proxy). O par com `username` evita que um usuário tranque os outros, mas o IP registrado fica inútil para auditoria de tentativa de invasão. Ajuste: instruir o axes a ler o IP real do encadeamento `X-Forwarded-For` com contagem de proxy explícita.

### 4.5. `.env.example`

Bloco de produção documentando cada variável e seu valor no Render.

### 4.6. Duas variáveis que derrubam o deploy em silêncio

#### `DJANGO_SETTINGS_MODULE`

[manage.py](../../../manage.py) usa `config.settings.development` por padrão, enquanto [config/wsgi.py](../../../config/wsgi.py) usa `config.settings.production`. A divergência é inofensiva no ambiente local, onde o `.env` resolve tudo — e destrutiva no Render, onde o `.env` não existe (é ignorado pelo git).

Sem `DJANGO_SETTINGS_MODULE=config.settings.production` definida no ambiente:

- `collectstatic` e `migrate` rodam com `DEBUG=True` e com o storage de estáticos **sem** o manifesto do WhiteNoise;
- o gunicorn sobe com `production.py` (pelo `wsgi.py`), que **exige** o manifesto;
- resultado: `Missing staticfiles manifest entry` em **toda página do sistema** — erro 500 generalizado, inclusive na tela de login.

A variável entra fixa no `render.yaml`.

#### `DJANGO_TRUST_PROXY_SSL_HEADER`

[config/settings/production.py](../../../config/settings/production.py) liga `SECURE_SSL_REDIRECT = True`, e só confia em `X-Forwarded-Proto` quando `DJANGO_TRUST_PROXY_SSL_HEADER` está ativa (ADR 0033, default desligado por segurança).

No Render, **essa variável precisa ser `True`**. Sem ela, o Django não enxerga que a requisição chegou por HTTPS, redireciona para HTTPS de novo, e o navegador entra em **loop infinito de redirecionamento** — o site simplesmente não abre, e a mensagem de erro não indica a causa.

A ADR 0033 está correta em manter o default desligado: só se ativa atrás de um proxy estrito que sanitize o header. O Render é um. A variável entra no `render.yaml` com valor fixo e vai destacada no guia de deploy.

## 5. Migrações e primeiro acesso

### 5.1. Migrações

Rodam no **pre-deploy command** (`uv run python manage.py migrate`), disponível em planos pagos, executado após o build e antes da versão nova entrar no ar. É o lugar recomendado pela documentação do Render e evita que uma migração falha publique código incompatível com o schema.

As data migrations existentes criam os **três grupos de permissão** — Administrador, Chefe de Gabinete e Assessor — já com a matriz da [docs/permissoes.md](../../permissoes.md) v2. Não há passo manual de configuração de perfis.

O disco persistente **não é acessível durante build nem pre-deploy**. Nenhuma das duas etapas toca em `MEDIA_ROOT`, então isso não impõe restrição.

### 5.2. Primeiro usuário

`accounts/management/commands/criar_usuarios_iniciais.py` exige `DEBUG=True` (ADR 0030, anti-backdoor) — corretamente inutilizável em produção.

Procedimento:

1. Pedro abre o **Shell do Render** (incluso no plano pago) e roda `uv run python manage.py createsuperuser` — e-mail e senha digitados por ele, nunca gravados em arquivo nem no histórico do repositório.
2. Entra pela interface e cadastra a equipe em `/configuracoes/`, atribuindo Chefe de Gabinete ou Assessor a cada pessoa.

O banco entra **vazio**. `criar_dados_teste` não roda em produção (também exige `DEBUG=True`).

## 6. Backup

**Camada 1 — automática, do Render.** Point-in-time recovery contínuo dos últimos 3 dias no workspace Hobby. Cobre o incidente comum: exclusão acidental, migração malsucedida, corrupção recente. A recuperação cria uma instância nova para validar antes de trocar, sem sobrescrever o banco vivo.

**Camada 2 — manual, mensal.** O painel do Render gera um export lógico completo (`.dir.tar.gz`) em um clique, retido 7 dias. Pedro baixa e guarda fora da plataforma **uma vez por mês**. Cobre a catástrofe rara: conta suspensa, falha de cobrança, decisão de sair da plataforma.

### 6.1. Divergência assumida do roadmap

O roadmap §4.6.2 item 3 pede backup automatizado com `pg_dump -Fc`, rotação (7 diários + 4 semanais) e criptografia at-rest. **Não será construído nesta entrega**, por três razões:

1. `scripts/backup.sh` é um script bash e **não roda no Windows de Pedro** como está — a automação existente é inoperante no ambiente do único operador.
2. Backup automatizado *para fora* do Render exige contratar armazenamento externo e gerenciar credenciais — mais superfície para administrar do que o volume de dados de um gabinete municipal justifica hoje.
3. As duas camadas acima cobrem os cenários reais de perda, com esforço operacional de um clique por mês.

Registrado na ADR e no débito técnico, não varrido para debaixo do tapete. O gatilho para revisitar: quando o volume de dados ou a criticidade tornarem a janela de 3 dias insuficiente.

## 7. Documentação a produzir

| Documento | Conteúdo |
|---|---|
| `docs/deploy.md` | Guia passo a passo, escrito para Pedro executar sozinho: criar o Blueprint, configurar variáveis, primeiro superusuário, cadastrar a equipe, procedimento mensal de backup, como trocar para domínio próprio no futuro, e **o que fazer quando cada etapa falhar** |
| `docs/decisoes.md` | ADR 0061 — Render via Blueprint; Docker adiado; backup por PITR + export manual; recuperação de senha no backlog |
| `roadmap.md` | Fase 7 atualizada: o que foi entregue, o que foi adiado e por quê |
| `docs/debito-tecnico.md` | DTs novos: backup automatizado off-site; recuperação de senha por e-mail; Dockerfile para portabilidade |

## 8. Fora de escopo

- **Docker** — adiado; entra como item de portabilidade quando houver motivo concreto para sair do Render
- **Recuperação de senha por e-mail** — funcionalidade nova, não existe no MPD hoje; backlog
- **Domínio próprio** — configuração fica parametrizada para receber, sem trabalho adicional
- **LGPD** — Fase 8 (ADR 0047)
- **Importação de dados existentes** — se houver base de contatos em planilha para carregar, é projeto próprio com seu ciclo de spec
- **CI/CD** — o Render já faz deploy automático a cada push no branch configurado; pipeline de testes em CI é item separado

## 9. Critérios de aceite

**Antes de subir:**

- [ ] `uv run pytest` — 239 testes verdes
- [ ] `uv run ruff check .` e `uv run black --check .` limpos
- [ ] `uv run python manage.py check --deploy` sem issues críticos
- [ ] `build.sh` roda localmente (em WSL/Git Bash) e produz `tailwind-output.css` não vazio

**Depois de subir (roteiro manual, executado por Pedro com acompanhamento):**

- [ ] `/healthz/` responde 200
- [ ] Home pública abre **com estilo aplicado** (valida o passo do Tailwind)
- [ ] Login do superusuário funciona
- [ ] Criar uma Pessoa, criar uma Demanda, enviar um anexo
- [ ] **Disparar um segundo deploy e confirmar que o anexo continua acessível** — este é o teste que prova o disco persistente
- [ ] Criar um usuário Assessor e confirmar que ele **não** enxerga demanda alheia nem as listas de pessoas/entidades (need-to-know, ADR 0059)
- [ ] Confirmar que Assessor não acessa `/analise`, `/auditoria` nem `/configuracoes/`
- [ ] Logs do serviço visíveis no painel do Render
- [ ] Export manual do banco baixado com sucesso ao menos uma vez

## 10. Riscos conhecidos

| Risco | Mitigação |
|---|---|
| Loop de redirecionamento por `DJANGO_TRUST_PROXY_SSL_HEADER` desligada | Valor fixo no `render.yaml` + destaque no guia |
| Erro 500 em toda página por `DJANGO_SETTINGS_MODULE` ausente | Valor fixo no `render.yaml` + linha própria na tabela de diagnóstico do guia |
| Erro 500 em toda pagina por `DJANGO_SETTINGS_MODULE` ausente | Valor fixo no `render.yaml` + linha propria na tabela de diagnostico |
| Site no ar sem CSS | `build.sh` compila o Tailwind; falha de download derruba o build em voz alta |
| Anexos perdidos | Disco persistente + critério de aceite que testa explicitamente sobrevivência a deploy |
| Custo escapando do previsto | Planos fixos; alerta de billing configurado no painel |
| Pedro travado numa etapa | `docs/deploy.md` traz seção de diagnóstico por sintoma, não só o caminho feliz |
