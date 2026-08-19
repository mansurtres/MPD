# Deploy do MPD no Render

> Guia para colocar e manter o MPD no ar. Escrito para ser executado por quem nunca fez deploy. Decisões e justificativas estão na ADR 0061 em [`decisoes.md`](./decisoes.md).

---

## 1. O que você vai ter no fim

Três peças rodando no Render, criadas de uma vez a partir do arquivo [`render.yaml`](../render.yaml):

| Peça | Plano | Custo/mês | Para quê |
|---|---|---|---|
| Web Service | Starter | ~US$ 7 | Roda o sistema |
| PostgreSQL | Basic-256mb | ~US$ 6 | Guarda os dados |
| Disco persistente | 1 GB | ~US$ 0,25 | Guarda os anexos |

**Total ~US$ 13,25/mês.** Endereço `https://mpd.onrender.com`, com HTTPS (o cadeado no navegador) automático e gratuito.

**Onde os dados ficam:** região da Virgínia, Estados Unidos. O Render não tem servidores na América do Sul. Consequência registrada na ADR 0061.

---

## 2. Antes de começar

- [ ] Conta criada no [render.com](https://render.com)
- [ ] O repositório do MPD está no GitHub, e a branch `main` contém o `render.yaml` (o Render lê o código de lá, não do seu computador)
- [ ] Você aceita que o sistema começa **vazio** — sem nenhuma pessoa, demanda ou usuário cadastrado

---

## 3. Criar tudo de uma vez

1. No painel do Render, clique em **New** → **Blueprint**
2. Conecte sua conta do GitHub e selecione o repositório do MPD
3. O Render lê o `render.yaml` e mostra o que vai criar: o serviço `mpd`, o banco `mpd-db` e o disco `mpd-media`. Confira se os três aparecem
4. Ele vai pedir o valor de quatro variáveis (as demais já vêm preenchidas):

   | Variável | O que preencher |
   |---|---|
   | `NOME_DO_MANDATO` | O nome completo do mandato, como aparece nos cabeçalhos |
   | `NOME_CURTO_DO_MANDATO` | Versão curta, para espaços apertados |
   | `SIGLA_MANDATO` | Sigla curta (ex.: `MPD`) |
   | `DEFAULT_FROM_EMAIL` | E-mail remetente do sistema |

5. Clique em **Apply**

A criação leva alguns minutos. **É normal o primeiro deploy falhar** se o banco ainda estiver sendo provisionado quando a aplicação tentar subir. Se isso acontecer, espere o banco ficar `available` e clique em **Manual Deploy** → **Deploy latest commit**.

### Se o nome `mpd` estiver ocupado

O endereço `mpd.onrender.com` é único no mundo inteiro do Render — se outra pessoa já usa, você precisa escolher outro. Três lugares precisam concordar entre si, no `render.yaml`:

- `name: mpd` (linha do serviço)
- `DJANGO_ALLOWED_HOSTS` → `seunome.onrender.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS` → `https://seunome.onrender.com`

Se os três não baterem, o site responde erro 400 ou recusa todos os formulários.

---

## 4. Criar o seu usuário

O sistema sobe sem nenhum usuário. O comando `criar_usuarios_iniciais` **não funciona em produção de propósito** (ADR 0030 — seria uma porta dos fundos). Então:

1. No painel, abra o serviço `mpd` → aba **Shell**
2. Rode:

   ```
   uv run python manage.py createsuperuser
   ```

3. Digite seu e-mail e escolha uma senha (mínimo 8 caracteres)

A senha é digitada por você e não fica gravada em lugar nenhum — nem em arquivo, nem no repositório, nem em conversa.

---

## 5. Cadastrar a equipe

Entre em `https://mpd.onrender.com` com o usuário que você acabou de criar, vá em **Configurações** → **Usuários** e crie cada pessoa da equipe, escolhendo o papel:

| Papel | O que enxerga |
|---|---|
| **Administrador** | Tudo, mais exportação, painel de análise, auditoria e configurações |
| **Chefe de Gabinete** | Todas as demandas ativas (sem o histórico concluído) |
| **Assessor** | Só as demandas próprias; o histórico próprio com as partes mascaradas |

Os três papéis já existem no sistema — você só atribui.

> ⚠️ **Não existe "esqueci minha senha".** Quem esquecer, você redefine em Configurações → Usuários. Foi uma decisão consciente para não depender de serviço de e-mail (ADR 0061); está registrada no débito técnico para revisão futura.

---

## 6. Backup

São duas camadas. A primeira é automática e você não precisa fazer nada.

**Camada 1 — automática.** O Render mantém backup contínuo do banco e permite voltar a **qualquer momento dos últimos 3 dias**. Cobre o acidente comum: alguém apagou o que não devia. Ao restaurar, o Render cria um banco novo com o estado escolhido, para você conferir antes de trocar — o banco atual não é sobrescrito.

**Camada 2 — manual, uma vez por mês.** Cobre a catástrofe rara (conta suspensa, problema de cobrança, decisão de sair do Render):

1. Painel → banco `mpd-db` → aba **Recovery**
2. **Create export**
3. Baixe o arquivo gerado e guarde fora do Render (seu computador, nuvem pessoal)

O arquivo fica disponível por 7 dias. **Coloque um lembrete mensal no seu calendário** — esta é a única tarefa recorrente que o sistema exige de você.

---

## 7. Quando algo der errado

Antes de qualquer coisa: painel → serviço `mpd` → aba **Logs**. A mensagem de erro está lá.

| O que você vê | Causa provável | O que fazer |
|---|---|---|
| "Redirecionou você muitas vezes" e o site não abre | `DJANGO_TRUST_PROXY_SSL_HEADER` não está `True` | Aba Environment → conferir o valor → Save (redeploy é automático) |
| Erro 500 em toda página, inclusive no login | `DJANGO_SETTINGS_MODULE` não está como `config.settings.production` — o `collectstatic` rodou no modo errado | Corrigir a variável → Manual Deploy |
| O site abre, mas sem nenhum estilo (texto cru) | O passo do Tailwind falhou no build | Ver o log do build: se o download do binário falhou, é só disparar Manual Deploy. O build aborta de propósito nesse caso, em vez de publicar sem CSS |
| "CSRF verification failed" ao salvar qualquer formulário | `DJANGO_CSRF_TRUSTED_ORIGINS` ausente ou com endereço diferente do real | Precisa ser `https://` seguido exatamente do endereço do serviço |
| Anexo enviado ontem sumiu hoje | O disco não está montado, ou `MEDIA_ROOT` aponta para fora dele | Confirmar que o disco `mpd-media` existe em `/var/data` e que `MEDIA_ROOT=/var/data/media` |
| "Bad Request (400)" ao abrir o site | O endereço não está em `DJANGO_ALLOWED_HOSTS` | Acrescentar o endereço exato do serviço |
| Deploy travado em "in progress", health check falhando | Banco ainda provisionando, ou uma migração falhou | Ver os Logs — a saída do pre-deploy mostra o erro exato da migração |
| O site fica ~1 min fora do ar a cada atualização | **Comportamento esperado**, não é defeito | Nada a fazer. É consequência do disco persistente, decisão registrada na ADR 0061 |
| Alguém não consegue entrar depois de errar a senha várias vezes | Bloqueio automático do django-axes: 5 tentativas, 30 min de espera | Esperar 30 min, ou destravar em `/admin/axes/` |

---

## 8. Atualizar o sistema depois

Todo `git push` para a branch `main` dispara um deploy automático. Acompanhe pela aba **Logs**.

Se uma atualização quebrar algo, o painel tem **Rollback** para voltar à versão anterior imediatamente — use sem hesitar, e só depois investigue.

---

## 9. Migrar para domínio próprio no futuro

Quando quiser trocar `mpd.onrender.com` por algo como `sistema.seumandato.com.br`:

1. Registre o domínio (registro.br, ~R$ 40/ano)
2. Painel → serviço `mpd` → **Settings** → **Custom Domains** → adicionar o domínio
3. O Render mostra qual registro DNS criar; crie-o no painel de onde você registrou o domínio
4. Acrescente o novo endereço em `DJANGO_ALLOWED_HOSTS` e `https://` + o endereço em `DJANGO_CSRF_TRUSTED_ORIGINS`

Nenhuma mudança de código. O certificado HTTPS é emitido automaticamente.

---

## 10. Referências

- [`render.yaml`](../render.yaml) — a infraestrutura declarada
- [`build.sh`](../build.sh) — o que roda a cada deploy
- [`.env.example`](../.env.example) — contrato de variáveis
- [`decisoes.md`](./decisoes.md) — ADR 0061 (este deploy), ADR 0033 (proxy SSL), ADR 0030 (usuários iniciais), ADR 0047 (LGPD na Fase 8)
- [`debito-tecnico.md`](./debito-tecnico.md) — o que foi adiado e sob qual gatilho revisitar
