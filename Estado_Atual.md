# PIPE — Estado Actual do Projecto — v1.3

## O que é o PIPE
Plataforma Inteligente Pessoal e Expansível — aplicação web Flask modular.
O nome é simultaneamente um acrónimo e o apelido do utilizador (Felipe = Pipe).
O módulo Euromilhões é o primeiro módulo, o módulo Tarefas é o segundo, o módulo Notas é o terceiro, o módulo Passwords é o quarto. O módulo Loja de Módulos é o sistema de personalização. O módulo Calendário é o oitavo módulo. O módulo Combustíveis é o nono módulo. A arquitectura suporta adição de novos módulos com a mesma identidade visual.

---

## O que foi feito

### Infraestrutura
- Repositório Git inicializado e publicado no GitHub: https://github.com/felipejn/pipe-app
- Suporte a `.env` com `python-dotenv` para gerir variáveis de ambiente localmente
- `.gitignore` configurado (exclui `.env`, `instance/`, `__pycache__`, `*.db`)
- `.env.example` incluído no repositório como referência
- **Deploy concluído no PythonAnywhere** — app online em `https://felipejn.pythonanywhere.com`

### Estrutura do projecto (Flask) — estado actual
```
pipe-app/
├── app/
│   ├── __init__.py          # create_app, app factory
│   ├── extensions.py        # Limiter (Flask-Limiter, X-Forwarded-For para PA)
│   ├── static/
│   │   ├── css/pipe.css     # design system (tema escuro, âmbar/dourado) + cores de eventos do Calendário
│   │   └── js/
│   │       ├── pipe.js      # JS base (alertas)
│   │       └── passwords.js # JS do módulo Passwords (não utilizado — JS inline no template)
│   ├── templates/
│   │   ├── base.html        # navbar sem links de módulos (navegação via dashboard)
│   │   ├── dashboard.html   # cards de módulos dinâmicos (Loja de Módulos)
│   │   ├── auth/
│   │   ├── euromilhoes/
│   │   ├── settings/
│   │   ├── admin/
│   │   │   ├── dashboard.html
│   │   │   ├── utilizadores.html
│   │   │   └── convites.html
│   │   ├── tarefas/
│   │   │   ├── index.html
│   │   │   ├── editar.html
│   │   │   └── _tarefa.html
│   │   ├── notas/
│   │   │   ├── index.html
│   │   │   ├── editar.html
│   │   │   └── _cartao.html
│   │   ├── passwords/
│   │   │   └── index.html
│   │   ├── cambio/
│   │   │   └── index.html
│   │   ├── modulos/
│   │   │   └── loja.html
│   │   └── calendario/
│   │       └── index.html   # vistas Agenda + Mensal, modal CRUD, JS inline
│   ├── combustiveis/        # Blueprint Combustíveis ← NOVO
│   │   ├── __init__.py
│   │   ├── models.py        # Posto, PrecoHistorico, UtilizadorConcelho, UtilizadorCombustivel, EstadoAtualizacaoCombustiveis
│   │   ├── services.py      # API Aberta (api.apiaberta.pt); atualizar_precos_se_necessario, obter_precos_para_concelhos, obter_tipos_combustivel_disponiveis
│   │   ├── routes.py        # /combustiveis/, /combustiveis/definicoes, /combustiveis/atualizar
│   │   └── templates/
│   │       └── combustiveis/
│   │           ├── dashboard.html
│   │           └── definicoes.html
│   ├── auth/                # Blueprint auth
│   │   ├── __init__.py
│   │   ├── routes.py        # /auth/login, /auth/registo (bloqueado), /auth/registo/<token>, /auth/logout, /auth/perfil, /auth/2fa/*
│   │   ├── forms.py
│   │   └── models.py        # modelo User (inclui is_admin) + Convite
│   ├── euromilhoes/         # Blueprint Euromilhões
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── models.py        # modelo Jogo (SQLite)
│   │   └── api.py           # consumo API pública + retry exponencial
│   ├── notifications/       # serviço central de notificações
│   │   ├── __init__.py
│   │   ├── service.py       # NotificationService
│   │   ├── models.py        # UserNotificationPreferences (BD)
│   │   └── channels/
│   │       ├── base.py
│   │       ├── telegram.py  # TelegramChannel
│   │       └── email.py     # EmailChannel (Mailjet)
│   ├── settings/            # Blueprint de definições
│   │   ├── __init__.py
│   │   └── routes.py        # /definicoes/
│   ├── admin/               # Blueprint de administração
│   │   ├── __init__.py
│   │   ├── decorators.py    # @admin_required
│   │   └── routes.py        # /admin/ — incluindo gestão de convites
│   ├── tarefas/             # Blueprint Tarefas
│   │   ├── __init__.py
│   │   ├── models.py        # Lista, Tarefa, TagTarefa
│   │   ├── forms.py         # ListaForm, TarefaForm
│   │   └── routes.py        # /tarefas/
│   ├── notas/               # Blueprint Notas
│   │   ├── __init__.py
│   │   ├── models.py        # Nota, ItemChecklist, EtiquetaNota
│   │   └── routes.py        # /notas/
│   ├── passwords/           # Blueprint Passwords
│   │   ├── __init__.py
│   │   ├── wordlist.py      # lista PT ~200 palavras para passphrases
│   │   ├── generator.py     # geração com secrets + cálculo de força por entropia
│   │   └── routes.py        # /passwords/
│   ├── cambio/              # Blueprint Câmbio
│   │   ├── __init__.py
│   │   └── routes.py        # /cambio/ — stateless, API ExchangeRate
│   ├── cores/               # Blueprint Cores Flutter
│   │   ├── __init__.py
│   │   └── routes.py        # /cores/ — stateless, HEX/RGB/HSL/CMYK para Flutter
│   ├── conversoes/          # Blueprint Conversões
│   │   ├── __init__.py
│   │   ├── models.py        # modelo Conversao (histórico, sem ficheiros)
│   │   └── routes.py        # /conversoes/ — HEIC→JPG + PNG/JPG→ICO
│   ├── modulos/             # Blueprint Loja de Módulos
│   │   ├── __init__.py
│   │   ├── config.py        # MODULOS_DISPONIVEIS (inclui Calendário)
│   │   ├── models.py        # UserModulo
│   │   └── routes.py        # /modulos/loja, /modulos/api/toggle
│   ├── assistente/          # Blueprint Assistente IA
│   │   ├── __init__.py
│   │   ├── cliente.py       # OpenRouter API
│   │   ├── contexto.py      # tool use orchestration
│   │   ├── ferramentas.py   # tool functions
│   │   └── routes.py        # /assistente
│   └── calendario/          # Blueprint Calendário ← NOVO
│       ├── __init__.py
│       ├── models.py        # modelo Evento
│       └── routes.py        # /calendario/ + /calendario/api/eventos (CRUD)
├── scripts/
│   ├── criar_admin.py
│   ├── promover_admin.py
│   ├── adicionar_is_admin.py
│   ├── migrar_notificada_em.py
│   ├── pipe_tasks.py        # única scheduled task
│   └── verificar_resultados.py  # mantido para referência histórica
├── instance/
│   └── pipe.db              # SQLite (excluído do git)
├── .env
├── .env.example
├── requirements.txt
└── run.py
```

---

### Módulo Auth (`app/auth/`)
- Modelo `User` com password em hash (Werkzeug)
- Campo `is_admin` — Boolean, default=False
- Novo modelo `Convite` — sistema de registo por convite (único, 7 dias de validade)
- Formulários: `LoginForm`, `RegistoForm`, `AlterarPasswordForm`, `VerificarCodigoForm`, `ConfigurarDoisFAForm`, `ConfirmarTOTPForm`, `PedirResetForm`, `ResetPasswordForm`
- Rotas: `/auth/login`, `/auth/registo` (bloqueado — requer convite), `/auth/registo/<token>`, `/auth/logout`, `/auth/perfil`
- Rotas 2FA: `/auth/2fa/verificar`, `/auth/2fa/escolher`, `/auth/2fa/enviar/<metodo>`, `/auth/2fa/reenviar`
- Rotas TOTP: `/auth/2fa/totp/configurar`, `/auth/2fa/totp/desactivar`
- Rotas recuperação de password: `/auth/recuperar-password`, `/auth/reset-password/<token>`
- **Registo aberto desativado** — apenas entrada por convite gerado por admin

### Módulo Euromilhões (`app/euromilhoes/`)
- Modelo `Jogo` (SQLite)
- `api.py` — consome a API pública com retry exponencial (3 tentativas, backoff 5s/10s/20s)
- Rotas: listar jogos, registar, apagar, gerar combinação, resultados, frequências
- Cálculo local do próximo sorteio (terça ou sexta)

### Módulo Tarefas (`app/tarefas/`)
- **Modelos:** `Lista`, `Tarefa` (com `notificada_em`), `TagTarefa`
- **Rotas:** criar/editar/apagar listas e tarefas, toggle concluída, adição rápida
- **Funcionalidades:** vista "Todas", busca em tempo real, filtros, secção de concluídas colapsável, modal de nova lista com selector de emoji
- **Comportamento ao abrir:** vista "Todas" por defeito — parâmetro `lista` tem default `'todas'` em `routes.py`
- **Mobile:** selector `<select>` acima da grelha, visível apenas em ecrãs ≤ 640px

### Módulo Loja de Módulos (`app/modulos/`)
- Tabela `UserModulo` (`user_id` + `modulo_slug` + `ativo`)
- `config.py` — dicionário `MODULOS_DISPONIVEIS` com 9 módulos (inclui Calendário)
- `models.py` — modelo `UserModulo` (PK composta) + helper `get_modulos_ativos(user_id)`
- `routes.py` — `GET /modulos/loja`, `POST /modulos/api/toggle` (AJAX + CSRF)
- Ícone 🛒 na navbar acessível a todos os utilizadores autenticados
- Zero módulos activos por defeito — dashboard mostra estado vazio com link para a loja

### Módulo Notas (`app/notas/`)
- **Modelos:** `Nota`, `ItemChecklist`, `EtiquetaNota`
- **Rotas:** `GET /notas/`, `POST /notas/criar`, `GET/POST /notas/<id>`, `POST /notas/<id>/accao`, `POST /notas/<id>/apagar`
- **Funcionalidades:** grelha de cartões, criação inline, texto livre e checklist, 8 cores, fixar/arquivar, etiquetas, busca em tempo real, toggle checklist no cartão

### Módulo Passwords (`app/passwords/`)
- **Sem BD** — módulo totalmente stateless
- **Modos:** Password (8–64 chars), Passphrase (3–10 palavras PT), PIN (4–12 dígitos)
- **Funcionalidades:** barra de força por entropia, botão copiar, geração automática ao carregar

### Módulo Câmbio (`app/cambio/`)
- **Sem BD** — módulo stateless
- **API externa:** Wise API v3 com fallback para ExchangeRate-API
- **Moedas:** EUR, BRL, USD, GBP, JPY, CHF, CAD, AUD
- **Funcionalidades:** fees Wise detalhados, inverter moedas, botão copiar

### Módulo Cores (`app/cores/`)
- **Sem BD** — módulo stateless
- **Funcionalidades:** Cor → Flutter (HEX/RGB/HSL/CMYK), Flutter → Cor, todos os equivalentes Flutter, preview em tempo real

### Módulo Conversões (`app/conversoes/`)
- **Modelo:** `Conversao` (metadados no histórico, sem ficheiros)
- **Conversões:** HEIC→JPG (`pillow_heif`), PNG/JPG→ICO (Pillow LANCZOS)
- **Funcionalidades:** dropzone drag & drop, download direto ou ZIP, zero disco

### Módulo Calendário (`app/calendario/`) ← NOVO — v1.2
- **Modelo:** `Evento` com campos: `id`, `user_id` (FK → `utilizadores.id`), `titulo`, `descricao`, `localizacao`, `data_inicio`, `data_fim`, `dia_inteiro`, `cor`, `notificar`, `notificado_em`, `criado_em`
- **Paleta de 11 cores:** tomate, flamingo, tangerina, banana, sálvia, basil, peacock, mirtilo, lavanda, uva, grafite
- **Rotas API:**
  - `GET /calendario/` — página principal (login required)
  - `GET /calendario/api/eventos?inicio=&fim=` — lista eventos do intervalo (60/min)
  - `POST /calendario/api/eventos` — criar evento (30/min)
  - `PUT /calendario/api/eventos/<id>` — editar evento (30/min)
  - `DELETE /calendario/api/eventos/<id>` — apagar evento (30/min)
- **Template `calendario/index.html`:**
  - **Vista Agenda** — lista cronológica a partir de hoje, agrupada por data, com hora início–fim, cor, localização; botões editar e apagar por evento
  - **Vista Mensal** — grelha 7×N (Seg–Dom), navegação mês anterior/seguinte/Hoje, pílulas coloridas com título, dia actual destacado (âmbar), clique em slot vazio pré-preenche data no modal
  - **Modal único** (criar e editar) — título, descrição, localização, datetime início/fim, toggle dia inteiro, toggle notificar, selector de 11 cores (círculos clicáveis), validação data_fim ≥ data_inicio, mensagem de erro inline
  - Frontend vanilla JS inline — padrão PIPE; CSRF via `X-CSRFToken` em todos os fetch
- **Integração na Loja de Módulos** — entrada em `MODULOS_DISPONIVEIS` com slug `calendario`
- **CSS** — 11 classes `.evento-<cor>` adicionadas ao `pipe.css`
- **Padrão de imports corrigido:** `from app import db` + `from app.extensions import limiter` (padrão PIPE)
- **Bug corrigido:** `#agenda-vazio` recriado via `innerHTML` a cada chamada `carregarAgenda()` para evitar perda de referência DOM ao alternar vistas

### Área Admin (`app/admin/`)
- Blueprint em `/admin`, decorador `@admin_required`
- Ícone 🛠️ na navbar visível apenas para admins
- Dashboard com estatísticas, lista de utilizadores, toggle activo/admin, apagar utilizador
- **Gestão de Convites:** `GET /admin/convites`, `POST /admin/convites/gerar`, `POST /admin/convites/<id>/revogar`
- Reutiliza `EmailChannel` (Mailjet) para envio automático de convites

### Módulo Assistente IA (`app/assistente/`) — em desenvolvimento
- **Sem BD** — histórico de conversa em Flask session (máx 20 mensagens)
- **Ficheiros:** `cliente.py` (OpenRouter API, retry 3x), `contexto.py` (tool use), `ferramentas.py` (4 tools: `get_tarefas`, `get_notas`, `get_euromilhoes`, `get_resumo_geral`), `routes.py`
- **Pendência:** conexão com API instável — retry/fallback a melhorar

### Sistema de notificações (`app/notifications/`)
- `NotificationService` — `notification_service.send(user, type, subject, body, data)`
- `TelegramChannel` ✅ e `EmailChannel` ✅ (Mailjet)
- `UserNotificationPreferences` na BD; página de definições em `/definicoes`

### Scheduled task — `scripts/pipe_tasks.py`
Script unificado que corre 1x/dia no PA (08:00). Cada módulo é uma função independente.

| Módulo | Quando actua | O que faz |
|---|---|---|
| `tarefa_euromilhoes` | Terças e sextas | Verifica resultados e notifica utilizadores com jogos |
| `tarefa_tarefas` | Todos os dias | Notifica tarefas em atraso (diariamente enquanto persistirem) |
| `tarefa_combustiveis` | **Terças-feiras** | Actualiza preços dos postos (via API Aberta api.apiaberta.pt), respeitando o intervalo mínimo de 1x/dia por terça; ignorado nos restantes dias |
| `tarefa_calendario_hoje` | **Pendente** | Notificar eventos do dia seguinte — **por implementar** |
### Autenticação 2FA
- Telegram ✅, Email ✅, TOTP ✅ (pyotp + qrcode)
- Múltiplos métodos em simultâneo — utilizador escolhe no login

### Design System (`app/static/css/pipe.css`)
- Tema escuro, acentos âmbar/dourado
- Componentes: navbar, cartões, formulários, botões, alertas, skeleton loader, toggles, modais
- Componentes Euromilhões: bolas, barras de frequência, badges de resultado
- Componentes Tarefas: sidebar, items, check circular, busca, badges, estado vazio, selector mobile
- Componentes Notas: grelha de cartões, palete de cores, checklist, sidebar de etiquetas
- **Componentes Calendário:** 11 classes `.evento-<cor>` (tomate → grafite) ← NOVO
- Layout responsivo (sidebar oculta em mobile)

### Módulo Combustíveis (`app/combustiveis/`) ← NOVO — v1.3
- **Schema:** tabelas `combustiveis_postos`, `combustiveis_precos_historico`, `combustiveis_utilizador_concelho`, `combustiveis_utilizador_combustivel` e `combustiveis_estado_atualizacao`. FK de utilizador aponta para `utilizadores.id` (nome real da tabela). `db.create_all()` cria as tabelas no primeiro reload (sem Flask-Migrate).
- **Modelo `Posto.id`** é o id da API Aberta; relacionamento `precos` lazy='dynamic'.
- **Serviço:** `services.atualizar_precos_se_necessario(forcar=False, hoje=None)` — corre **só às terças-feiras** (e só uma vez por dia, via `estado.ultima_atualizacao.date() == hoje`); o botão manual "Actualizar Dados" (`forcar=True`) ignora o dia. Faz paginação completa da API Aberta (`GET /v1/fuel/stations?fuel=<slug>&page=&limit=100`) por combustível, filtra cliente `municipality` para Braga/Vila Verde/Amares e grava em `Posto` + `PrecoHistorico` (upsert por `station_id`). Autenticação via header `X-API-Key` (var `APIABERTA_API_KEY`, opcional — sem chave = 30 pedidos/min; com chave = 300/min). `obter_precos_para_concelhos(concelhos, tipos_utilizador, tipo_selecionado)` devolve o preço mais recente por posto+combustível; o dropdown `?combustivel=` filtra *dentro* do universo de tipos do utilizador. `obter_tipos_combustivel_disponiveis` lista os tipos do universo.
- **Rotas:**
  - `GET /combustiveis/` — dashboard: cards "Mais barato por combustível" + tabela (Posto | Concelho | Combustível | Preço (€/L) | Data); filtro GET `?combustivel=`; redirect para Definições se sem concelhos.
  - `GET/POST /combustiveis/definicoes` — checkboxes de concelhos + combustíveis; gravação em `UtilizadorConcelho` e `UtilizadorCombustivel` (delete+insert, como nas outras definições).
  - `POST /combustiveis/atualizar` — força a actualização e faz redirect.
- **Templates** em `app/templates/combustiveis/{dashboard,definicoes}.html` (arranjo do PIPE: `app/templates/<modulo>/`).
- **CSS:** reutiliza as classes existentes (`pipe.css`) — `.cartao`, `.admin-tabela`, `.opcao-check`, `.btn`, `.campo-texto`, `.secao-*`. Dropdown usa `class="campo-texto"` e GET (sem CSRF).
- **Scheduled task:** `tarefa_combustiveis` em `scripts/pipe_tasks.py` — chama `services.atualizar_precos_se_necessario(forcer=False)`; log "Hoje não é terça-feira — actualização automática ignorada." quando fora de terça.
 - **Primeira recolha:** correu uma vez manualmente via `services.atualizar_precos_se_necessario(forcar=True)` (equivalente a `scripts/popular_combustiveis.py`). Substitui o antigo `scripts/mapear_combustiveis_inicial.py` (removido — não era necessário com a API Aberta: a paginação por combustível já devolve os postos da zona directamente).
- **Integração na Loja:** entrada em `MODULOS_DISPONIVEIS` com slug `combustiveis`, ícone ⛽, rota `combustiveis.dashboard`.

### Segurança

| Medida | Implementação | Ficheiro |
|---|---|---|
| CSRF | Flask-WTF CSRFProtect em todos os formulários | `app/__init__.py` |
| Rate limiting | Flask-Limiter nas rotas críticas | `app/auth/routes.py`, `app/extensions.py` |
| Logging de login falhado | `app.logger.warning` com username e IP | `app/auth/routes.py` |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | `app/__init__.py` |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` | `app/auth/models.py` |
| Controlo de acesso | `@login_required` e `@admin_required` | rotas protegidas |
| Configuração IP PA | `X-Forwarded-For` no Limiter | `app/extensions.py` |

### Testes realizados
- Login e registo ✅
- Dashboard com cards de módulos ✅
- Módulo Loja de Módulos — activar/desactivar módulos ✅
- Dashboard dinâmico — estado vazio + cards por módulos activos ✅
- Módulo Euromilhões completo ✅
- 2FA Telegram, Email, TOTP ✅
- Recuperação de password por email ✅
- Notificações Telegram e Email (manual) ✅
- Área admin completa ✅
- Sistema de Convites ✅
- Módulo Tarefas completo ✅
- `pipe_tasks.py` com módulo Tarefas ✅
- Módulo Notas completo ✅
- Módulo Passwords completo ✅
- Módulo Câmbio — conversão EUR → BRL ✅
- **Módulo Calendário — Vista Agenda** ✅ (criar, editar, apagar, agrupamento por data)
- **Módulo Calendário — Vista Mensal** ✅ (grelha 7×N, navegação, pílulas coloridas, clique em slot)
- **Módulo Calendário — Modal CRUD** ✅ (validação, selector de cor, toggles)
- **Módulo Calendário — alternância Agenda ↔ Mensal** ✅ (bug DOM corrigido)
- **Módulo Combustíveis — dashboard com filtro `?combustivel=`** ✅
- **Módulo Combustíveis — definições com checkboxes de concelhos + combustíveis** ✅
- **Módulo Combustíveis — `tarefa_combustiveis` às terças** ✅ (ignora fora de terça; força no botão manual)

---

## Deploy — PythonAnywhere

### Estado
- **App online** em `https://felipejn.pythonanywhere.com` ✅
- **WSGI configurado** ✅
- **Static files** configurados ✅
- **Scheduled task** — `python /home/felipejn/pipe-app/scripts/pipe_tasks.py` às 08:00 ✅
- **Módulo Calendário — deploy e migração de BD pendentes** ⚠️

### Configuração WSGI
```python
import sys, os
from dotenv import load_dotenv

project_home = '/home/felipejn/pipe-app'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

load_dotenv(os.path.join(project_home, '.env'))

from app import create_app
application = create_app()
```

### Variáveis de ambiente no PA (`.env`)
```
FLASK_ENV=production
SECRET_KEY=<gerado com secrets.token_hex(32)>
TELEGRAM_BOT_TOKEN=...
MAILJET_API_KEY=...
MAILJET_API_SECRET=...
MAILJET_FROM_EMAIL=...
WISE_API_KEY=...
APIABERTA_API_KEY=...
```

### Migrações de BD executadas
- `scripts/adicionar_is_admin.py` ✅
- `scripts/migrar_notificada_em.py` ✅
- Módulo Notas — tabelas criadas por `db.create_all()` ✅
- Módulo Loja — tabela `user_modulos` criada por `db.create_all()` ✅
- Módulo Passwords — sem BD ✅
- **Módulo Calendário — tabela `evento` a criar no PA após deploy** ⚠️
- **Módulo Combustíveis — 4 tabelas** (`combustiveis_postos`, `combustiveis_precos_historico`, `combustiveis_utilizador_concelho`, `combustiveis_utilizador_combustivel`, `combustiveis_estado_atualizacao`) criadas por `db.create_all()` no primeiro reload; modelo `UtilizadorCombustivel` adicionado ao import de `db.create_all()` em `app/__init__.py` ✅

### Comando de migração do Calendário (executar no PA após deploy)
```bash
python -c "from app import create_app; from app.extensions import db; from app.calendario.models import Evento; app = create_app(); app.app_context().push(); db.create_all()"
```

### Módulo Combustíveis (migração)
As tabelas do módulo Combustíveis são criadas **automaticamente** pelo `db.create_all()` (já chamado no arranque da app e com os modelos importados em `app/__init__.py`), **sem necessidade de script de migração manual**. A primeira população de dados é feita uma única vez correndo `services.atualizar_precos_se_necessario(forcar=True)` — ou, por conveniência, `python scripts/popular_combustiveis.py` (script de ajuda, não obrigatório). No deploy do PA, basta o primeiro reload — as 4 tabelas + a linha seed `id=1` de `EstadoAtualizacaoCombustiveis` são criadas. **`api.apiaberta.pt` está na whitelist do PA** (é um domínio com documentação Swagger pública, diferentemente da DGEG que o substituiu).

---

## Arquitectura de módulos

Cada módulo é um Flask Blueprint independente. A navegação é feita pelos cards no dashboard.

**Para adicionar um novo módulo:**
1. Criar `app/<modulo>/` com `__init__.py` e `routes.py` (+ `models.py` se precisar de BD)
2. Registar o blueprint em `app/__init__.py`
3. Adicionar entrada em `app/modulos/config.py`
4. Adicionar CSS específico em `pipe.css` se necessário
5. Adicionar função `tarefa_<modulo>()` em `scripts/pipe_tasks.py` se precisar de tarefa agendada

**Padrão AJAX/fetch no PIPE:**
- Passar sempre `'X-CSRFToken': '{{ csrf_token() }}'` no header do fetch
- Backend usa `request.get_json()` — não usa `validate_on_submit()`

**Padrão de imports nos blueprints:**
- `from app import db` — para SQLAlchemy
- `from app.extensions import limiter` — para rate limiting

---

## Ponto onde estamos

**Versão v1.3** — nove módulos completos (oito deployed + Calendário local; mais o módulo **Combustíveis**, local). Módulo Calendário implementado com vistas Agenda e Mensal, CRUD completo via API, modal único, paleta de 11 cores e integração na Loja de Módulos. Módulo Combustíveis implementado com recolha via **API Aberta** (`api.apiaberta.pt/v1/fuel/stations`, autenticada com `X-API-Key`) para Braga/Vila Verde/Amares, dashboard filtrado, definições de concelhos+combustíveis e tarefa agendada às terças. Primeira recolha concluída com **95 postos** e **1480 preços históricos**. Commit `7f6e871` no branch `main`.

**Pendências do Calendário:**
- `tarefa_calendario_hoje()` em `pipe_tasks.py` — notificação de eventos do dia seguinte às 08:00
- Deploy no PythonAnywhere + migração da tabela `evento`
- **Backlog v1.x:** tela de detalhe do evento (read-only, acionada ao clicar no evento na Agenda ou Vista Mensal; botão "Editar" dentro do detalhe abre o modal existente)

**Pendências gerais:**
- **Assistente IA:** conexão com API instável — melhorar retry/fallback
- **Módulos futuros:** arquitectura pronta — versão 1.x

---

## Próximos passos imediatos

1. Módulo Combustíveis — primeira recolha manual concluída ✅ (95 postos, 1480 preços; fonte: API Aberta)
2. Deploy do módulo Combustíveis no PythonAnywhere + `db.create_all()` para criar as tabelas (funciona no primeiro reload, sem migração manual)
   - `api.apiaberta.pt` já está na whitelist do PA (documentação Swagger pública)
   - Definir `APIABERTA_API_KEY` no `.env` do PA e Reload da web app (sem a chave, 30 pedidos/min; com chave, 300/min e ~25s por recolha)
3. Implementar `tarefa_calendario_hoje()` em `scripts/pipe_tasks.py`
4. Deploy do Calendário no PythonAnywhere
5. Migração da tabela `evento` no PA
6. Testar notificações do Calendário em produção

---

## Dependências actuais
```
Flask==3.0.3
Flask-Login==0.6.3
Flask-WTF==1.2.1
Flask-SQLAlchemy==3.1.1
Werkzeug==3.0.3
WTForms==3.1.2
python-dotenv==1.0.1
requests==2.32.3
email-validator==2.2.0
pyotp==2.9.0
qrcode==7.4.2
pillow==10.4.0
Flask-Limiter==3.8.0
```

## Contexto técnico
- Python com ortografia Portuguesa Europeia em todos os comentários e mensagens ao utilizador
- Hosting: PythonAnywhere (plano free) — `https://felipejn.pythonanywhere.com`
- Custo total: zero
- Base de dados: SQLite
- Autenticação: username/password + 2FA opcional (Telegram ✅, Email ✅, TOTP ✅) + recuperação de password por email ✅
- Notificações: Telegram ✅ + Mailjet email ✅ — arquitectura modular, canais independentes
- Admin: área restrita com gestão de utilizadores + sistema de convites, decorador `@admin_required`
- Scheduled task: `pipe_tasks.py` — script unificado, um módulo por função, isolamento de erros
- Rate limiting: Flask-Limiter com `X-Forwarded-For` para PythonAnywhere
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`
- Login event logging: tentativas falhadas registadas com username e IP via `app.logger.warning`
