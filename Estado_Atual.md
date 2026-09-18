# PIPE — Estado Actual do Projecto — v1.4.6

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
│   │   ├── css/pipe.css     # design system (tema escuro + tema claro via tokens semânticos) + cores de eventos do Calendário + navegação secundária
│   │   ├── icons/           # icon-192.png, icon-512.png (PWA)
│   │   ├── manifest.json    # PWA — manifest
│   │   ├── sw.js            # PWA — service worker (network-first para CSS/JS/HTML, cache pipe-v3)
│   │   └── js/
│   │       └── pipe.js      # JS base (alertas + alternância de tema claro/escuro)
│   ├── templates/
│   │   ├── base.html        # navbar + alternador de tema 🌙/☀️ + anti-FOUC + barra secundária «Voltar/Home» (oculta no dashboard)
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
│   ├── popular_combustiveis.py  # recolha manual de combustíveis (helper)
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
- **Funcionalidades:** grelha de cartões, criação inline, texto livre e checklist, 8 cores (paleta Google Keep — claro + escuro, texto forçado a preto sobre cores claras para contraste), fixar/arquivar, etiquetas, busca em tempo real, toggle checklist no cartão

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
- **Ficheiros:** `cliente.py` (OpenRouter API, retry 3x + fallback entre modelos), `contexto.py` (tool use + logging de erro), `ferramentas.py` (5 tools de leitura: `get_tarefas`, `get_notas`, `get_euromilhoes`, `get_resumo_geral`, `get_eventos`; 10 tools de escrita), `routes.py`
- **Modelo:** `inclusionai/ling-3.0-flash-fin:free` (1.11T tokens, 262K ctx) — configurado via `OPENROUTER_MODEL` env var. Fallbacks: `nex-agi/nex-n2.5-mini:free`, `inclusionai/ling-3.0-flash-sante:free`, `liquid/lfm-2.5-2.6b:free`, `nvidia/nemotron-3-super-120b-a12b:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`
- **Correção aplicada (v1.4.0):** o modelo anterior (`google/gemma-4-26b-a4b-it:free`) não suportava tool use, causando falhas silenciosas com a mensagem genérica de erro. Trocado para `google/gemma-4-31b-it:free`. Removidos modelos inválidos (`qwen/qwen3.6-plus:free`, `qwen/qwen3-coder:free`). Adicionado `import traceback` e `traceback.print_exc()` + `print(f'[Assistente ERRO] ...')` nos blocos `except Exception` de `contexto.py` para diagnóstico visível nos logs. Simplificado tratamento de HTTP 429 (break imediato para próximo modelo, sem parsing de `Retry-After` header)
- **Correção de bug crítica (v1.4.4):** `processar_mensagem_assistente('cria um evento para amanhã: "Cortar cabelo" às 9 horas')` devolvia "Não consegui gerar uma resposta" em vez de criar o evento. Diagnóstico: o OpenRouter devolve HTTP 200 com corpo `{"error": ...}` quando o provider upstream falha; o código original só fazia `raise_for_status()` (200 passava como sucesso) e `raise_for_status()` estava fora do `try`, abortando a cadeia de fallback. Correção em `app/assistente/cliente.py`: classes `RateLimitError` e `ServicoIndisponivelError`, constante `_MODELOS_FALLBACK`, função `_classificar_resposta()` que valida HTTP e corpo da resposta (distinguindo `rate_limit` / `modelo_indisponivel` / `servico` / `ok`), `chamar_llm()` com fallback imediato em qualquer falha de provider e backoff apenas para exceções de rede. Reforço em `app/assistente/contexto.py`: parsing defensivo de `choices` (verificação de tipo), `tool_calls` com validação de tipo, `content` vazio aceite, `argumentos` aceita `str` ou `dict`, `ServicoIndisponivelError` tratado no ciclo. Validação: 21 testes unitários offline passaram; smoke test real contra OpenRouter com `cohere/north-mini-code:free` criou evento com sucesso (ID 4).

- **Implementação (v1.4.5):** adicionada ferramenta de leitura `get_eventos` ao Assistente IA. O calendário era o único módulo sem ferramenta de consulta. Adicionados em `app/assistente/ferramentas.py`: schema JSON em `DEFINICOES_FERRAMENTAS_LEITURA`, entrada em `REGISTO_FERRAMENTAS`, e função `get_eventos(user_id, data=None, futuros=False)` com query filtrada por `user_id`, data específica (AAAA-MM-DD) e eventos futuros. Correcção do import `from datetime import date, datetime, timedelta`.
    - **Teste:** import verificado com sucesso — `get_eventos` presente em `REGISTO_FERRAMENTAS` e `DEFINICOES_FERRAMENTAS_LEITURA`

- **Correção (v1.4.6):** o Assistente IA respondia com atraso porque o `.env` tinha `OPENROUTER_MODEL=thinkingmachines/inkling-small:free`. Esses modelos são restritos a *agentic harnesses* e devolvem HTTP 403 ("is only available on agentic harnesses") quando chamados por aplicações comuns — cada pergunta perdia tempo nessa falha antes de cair no fallback. Além disso, o ID `liquid/lfm2.5-2.6b:free` na fila era inválido (HTTP 400 "is not a valid model ID").
    - **Correção 1 (causa raiz):** `OPENROUTER_MODEL` actualizado para `inclusionai/ling-3.0-flash-fin:free` em `.env` e `.env.example`. A variável de ambiente sobrepõe o default do código, pelo que era ela que mantinha os modelos `thinkingmachines` em primeiro lugar; o default no código (`cliente.py`) foi alterado em simultâneo para o mesmo valor, para os dois ficarem coerentes.
    - **Correção 2:** removidos os modelos `thinkingmachines/*` de `_MODELOS_FALLBACK`. Corrigido o ID de `liquid/lfm2.5-2.6b:free` para `liquid/lfm-2.5-2.6b:free` (hífen em falta).
    - **Fila final (ordem de preferência):** `inclusionai/ling-3.0-flash-fin:free` → `nex-agi/nex-n2.5-mini:free` → `inclusionai/ling-3.0-flash-sante:free` → `liquid/lfm-2.5-2.6b:free` → `nvidia/nemotron-3-super-120b-a12b:free` → `nvidia/nemotron-3-ultra-550b-a55b:free` (último recurso, mais lento).
    - **Validação:** IDs confirmados no catálogo do OpenRouter (`/api/v1/models`, 445 modelos) — todos gratuitos, contexto ≥65K e suporte a `tools`. Smoke test real: os 6 modelos responderam (0.7s–1.6s cada); no fluxo `chamar_llm(..., ferramentas=...)` o `inclusionai/ling-3.0-flash-fin:free` respondeu em **0.9s**, chamou a ferramenta correctamente e devolveu texto em PT-PT. 22 testes unitários passaram.

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
- Tema escuro (por defeito) e tema claro — acentos âmbar/dourado mantêm-se nos dois
- **Tokens semânticos em `:root`:** superfícies (`--cor-superficie`, `--cor-superficie-2`), bordas (`--cor-borda`, `--cor-borda-hover`), texto (`--cor-texto`, `--cor-texto-suave`, `--cor-texto-subtil(-2)`), estados (`--cor-sucesso/erro/info/aviso-texto`), prioridades (alta/média/baixa), `--cor-overlay-hover`, `--sombra` — ~23 cores fixas substituídas por variáveis
- **Tema claro via `[data-theme="light"]`** — sobrepõe apenas os tokens; o `data-theme` é definido no `<html>` antes do CSS (script anti-FOUC no `base.html` lê `localStorage['pipe-tema']`, default `dark`)
- Cores de identidade preservadas nos dois temas: âmbar (`--cor-primaria`), 11 classes `.evento-*` do Calendário, bolas do Euromilhões, `#1a1000` sobre âmbar no `.btn-primario`
- `.btn-tema` — botão de alternância na navbar (fundo transparente, `--cor-overlay-hover` no hover)
- Componentes: navbar, cartões, formulários, botões, alertas, skeleton loader, toggles, modais
- Componentes Euromilhões: bolas, barras de frequência, badges de resultado
- Componentes Tarefas: sidebar, items, check circular, busca, badges, estado vazio, selector mobile
- Componentes Notas: grelha de cartões, palete de cores, checklist, sidebar de etiquetas, 8 cores alinhadas à paleta Google Keep (`#F28B82`, `#FBBC05`, `#FFF475`, `#CCFF90`, `#CBF0F8`, `#D7AEFB`, `#E8EAED`) aplicáveis em tema claro e escuro ✅ — texto forçado a preto em cartões coloridos via `.nota-com-cor` para garantir contraste em ambos os temas
- **Componentes Calendário:** 11 classes `.evento-<cor>` (tomate → grafite) ← NOVO
- Layout responsivo (sidebar oculta em mobile)

### Interface / Navegação (frontend — sessão paralela)
- **Barra secundária «Voltar / Home»** em `base.html`: renderizada em todas as páginas excepto o dashboard (`{% if request.endpoint != 'dashboard' %}`); «← Voltar» usa `javascript:history.back()` e «Home» aponta para `url_for('dashboard')`.
- **Estilos CSS:** `.nav-secundaria` (barra com fundo `--cor-superficie` e borda inferior) e `.nav-link-secundario` (+ `:hover` com sublinhado), em `pipe.css`.
- **Alternador de tema (v1.4):** botão 🌙/☀️ em `.navbar-utilizador` (entre ⚙️ Definições e «Sair»); lógica centralizada em `pipe.js` (IIFE com guarda `if (!btn) return`): alterna `data-theme` entre `light`/`dark`, grava em `localStorage['pipe-tema']` e troca o ícone ☀️/🌙
- **Anti-FOUC:** script inline no `<head>`, antes do `pipe.css`, aplica o tema guardado antes do primeiro paint (evita flash de tema errado ao carregar)
- **PWA (já presente em `app/static/`):** `manifest.json`, `sw.js` (service worker, registado no `base.html`; desde a v1.4 **network-first para CSS/JS/HTML** com cache `pipe-v3` — garante que alterações de estilos chegam aos clientes após deploy; cache-first só como fallback offline) e ícones `icons/icon-192.png` / `icons/icon-512.png` — inclui `theme-color` âmbar e modo standalone em iOS.

### Módulo Combustíveis (`app/combustiveis/`) ← NOVO — v1.3
- **Schema:** tabelas `combustiveis_postos`, `combustiveis_precos_historico`, `combustiveis_utilizador_concelho`, `combustiveis_utilizador_combustivel` e `combustiveis_estado_atualizacao`. FK de utilizador aponta para `utilizadores.id` (nome real da tabela). `db.create_all()` cria as tabelas no primeiro reload (sem Flask-Migrate).
- **Modelo `Posto.id`** é o id da API Aberta; relacionamento `precos` lazy='dynamic'.
- **Serviço:** `services.atualizar_precos_se_necessario(forcar=False, hoje=None)` — corre **só às terças-feiras** (e só uma vez por dia, via `estado.ultima_atualizacao.date() == hoje`, marcador gravado apenas em execuções com sucesso, para permitir retry no mesmo dia após falha); o botão manual "Actualizar Dados" (`forcar=True`) ignora o dia. Faz paginação completa da API Aberta (`GET /v1/fuel/stations?fuel=<slug>&district=Braga&page=&limit=100`) por combustível (~12 pedidos, ~3-4 s por recolha), filtra do lado do cliente por `municipality` (Braga/Vila Verde/Amares) e grava em `Posto` + `PrecoHistorico` (chave `station_id`); só grava novo histórico quando `preco` ou `updated_at` mudam (deduplicação). Autenticação via header `X-API-Key` (var `APIABERTA_API_KEY`, opcional — sem chave = 30 pedidos/min; com chave = 300/min). `obter_precos_para_concelhos(concelhos, tipos_utilizador, tipo_selecionado)` devolve o preço mais recente por posto+combustível; o dropdown `?combustivel=` filtra *dentro* do universo de tipos do utilizador. `obter_tipos_combustivel_disponiveis` lista os tipos do universo. Devolve `postos_verificados`, `precos_novos` e `postos_na_bd` (mantém `postos_atualizados` por compatibilidade).
- **Rotas:**
  - `GET /combustiveis/` — dashboard: cards "Mais barato por combustível" + tabela (Posto | Concelho | Combustível | Preço (€/L) | Data); filtro GET `?combustivel=`; redirect para Definições se sem concelhos.
  - `GET/POST /combustiveis/definicoes` — checkboxes de concelhos + combustíveis; gravação em `UtilizadorConcelho` e `UtilizadorCombustivel` (delete+insert, como nas outras definições).
  - `POST /combustiveis/atualizar` — força a actualização (rate limit 6/hora) e faz redirect, com flash honesto ("X postos verificados, Y registos novos" ou "sem alterações desde a última recolha").
- **Templates** em `app/templates/combustiveis/{dashboard,definicoes}.html` (arranjo do PIPE: `app/templates/<modulo>/`).
- **CSS:** reutiliza as classes existentes (`pipe.css`) — `.cartao`, `.admin-tabela`, `.opcao-check`, `.btn`, `.campo-texto`, `.secao-*`. Dropdown usa `class="campo-texto"` e GET (sem CSRF).
- **Scheduled task:** `tarefa_combustiveis` em `scripts/pipe_tasks.py` — chama `services.atualizar_precos_se_necessario(forcar=False)`; log "Actualização automática ignorada — hoje não é terça-feira." quando fora de terça e "— já actualizado hoje" quando já correu nessa terça; em execução, loga postos verificados, registos novos e total na BD.
- **Correcções v1.3.1 (após o refactor para a API Aberta):**
  - **Bug crítico de paginação corrigido** — o `return encontrados` de `_paginar_fuel` estava indentado *dentro* do `while True`, devolvendo logo após a página 1. A recolha via API Aberta via apenas 4 postos (de 95) e o botão manual respondia "Preços atualizados (4 postos)." em ~1 s. Corrigido (return ao nível da função) e adicionada guarda `PAGINAS_MAX = 60`.
  - **Filtro `district`** — a API honra `district` (não honra `municipality`, `municipio`, `concelho`, `q` ou `search`). Com `district=Braga` a paginação passa de ~96 para ~12 pedidos (~21 s → ~3 s). O match é por prefixo (devolve também Bragança), pelo que o filtro por concelho continua a ser aplicado do lado do cliente.
  - **Deduplicação de histórico** — só se grava `PrecoHistorico` quando `preco` ou `data_atualizacao_dgeg` (o `updated_at` da API) difere do último registo do mesmo posto+combustível. Evita linhas 100% duplicadas (as recolhas DGEG tinham triplicado o histórico).
  - **Retorno honesto** — `atualizar_precos_se_necessario` devolve `postos_verificados`, `precos_novos` e `postos_na_bd` (mantém `postos_atualizados` por compatibilidade). O flash distingue "Preços actualizados — X postos verificados, Y registos novos." de "Preços verificados — X postos, sem alterações desde a última recolha."
  - **Estado visível** — o dashboard mostra "Última actualização: … · N postos na base de dados" e o erro da última recolha, se existir.
  - **`ultima_atualizacao` só é marcada em caso de sucesso** — uma falha na terça permite retry no mesmo dia (antes, a falha às 08:00 bloqueava o resto do dia).
  - **Rate limit** — `POST /combustiveis/atualizar` limitado a 6/hora (`@limiter.limit`).
- **Primeira recolha:** correu uma vez manualmente via `services.atualizar_precos_se_necessario(forcar=True)` (equivalente a `scripts/popular_combustiveis.py`). Substitui o antigo `scripts/mapear_combustiveis_inicial.py` (removido — não era necessário com a API Aberta: a paginação por combustível já devolve os postos da zona directamente).
- **Integração na Loja:** entrada em `MODULOS_DISPONIVEIS` com slug `combustiveis`, ícone ⛽, rota `combustiveis.dashboard`.

### Segurança

| Medida | Implementação | Ficheiro |
|---|---|---|
| CSRF | Flask-WTF CSRFProtect em todos os formulários | `app/__init__.py` |
| Rate limiting | Flask-Limiter nas rotas críticas | `app/auth/routes.py`, `app/combustiveis/routes.py`, `app/extensions.py` |
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
- **Módulo Combustíveis — paginação completa + deduplicação** (95 postos verificados num só ciclo, histórico sem linhas duplicadas, filtro `district`)
- **Tema claro/escuro — alternância via botão na navbar** ✅ (tema e ícone mudam; escolha persiste após reload via `localStorage`)
- **Tema claro/escuro — anti-FOUC** ✅ (tema aplicado antes do primeiro paint, sem flash)
- **Módulo Notas — paleta de cores Google Keep** ✅ (8 cores substituíram as cores escuras anteriores; aplicáveis em tema claro e escuro, sem alteração de BD — `Nota.CORES`, `_cartao.html`, `index.html` actualizados; `editar.html` usa a mesma fonte via `|tojson`)
- **Módulo Notas — contraste de texto em cartões coloridos** ✅ (texto forçado a preto via `.nota-com-cor` / `var(--nota-texto, var(--cor-texto))` sobre fundos claros; `_cartao.html` (grelha), e editor completo `editar.html` — `.nota-editar-titulo`, `.nota-editar-textarea`, `.checklist-editar-input`); garante legibilidade em tema claro e escuro


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

**Versão v1.4.6** — correção da lentidão do Assistente IA. O `OPENROUTER_MODEL` do `.env` ainda apontava para `thinkingmachines/inkling-small:free`, modelo restrito a *agentic harnesses* que devolve HTTP 403 em aplicações comuns — cada pergunta perdia tempo nessa falha antes de cair no fallback. Substituído por `inclusionai/ling-3.0-flash-fin:free` (`.env` e `.env.example`) e removidos os modelos `thinkingmachines/*` da fila de fallback; corrigido o ID inválido `liquid/lfm2.5-2.6b:free` → `liquid/lfm-2.5-2.6b:free`. IDs validados contra o catálogo do OpenRouter e por smoke test real (resposta em 0.9s com tool use em PT-PT). 22 testes unitários a passar. Sem alteração de BD.

**Versão v1.4.5** — implementação da ferramenta de leitura `get_eventos` para o Assistente IA, exibição do modelo no chat e conclusão de auditoria e limpeza de ficheiros obsoletos. Adicionada a 5.ª ferramenta de leitura do assistente (`get_eventos(user_id, data=None, futuros=False)`), preenchendo a lacuna do Calendário. No chat do assistente, adicionada indicação visual do modelo utilizado (`<small class="chat-modelo">`). Concluída a auditoria de ficheiros do repositório: removidos ficheiros de código morto/residuais (`app/static/js/passwords.js`, `scripts/adicionar_is_admin_local.py`, scripts de depuração de rede do OpenRouter) e organizados briefings antigos para `docs/historico/`. Suite automatizada de testes `pytest` validada com 22 testes unitários a passar. Sem alteração de BD.

**Versão v1.4.4** — correção de bug crítico no Assistente IA. `processar_mensagem_assistente('cria um evento para amanhã: "Cortar cabelo" às 9 horas')` devolvia "Não consegui gerar uma resposta" em vez de criar o evento. Diagnóstico: o OpenRouter devolve HTTP 200 com corpo `{"error": ...}` quando o provider upstream falha; o código original só fazia `raise_for_status()` (200 passava como sucesso) e `raise_for_status()` estava fora do `try`, abortando a cadeia de fallback. Correção em `app/assistente/cliente.py`: classes `RateLimitError` e `ServicoIndisponivelError`, constante `_MODELOS_FALLBACK`, função `_classificar_resposta()` que valida HTTP e corpo da resposta (distinguindo `rate_limit` / `modelo_indisponivel` / `servico` / `ok`), `chamar_llm()` com fallback imediato em qualquer falha de provider e backoff apenas para exceções de rede. Reforço em `app/assistente/contexto.py`: parsing defensivo de `choices` (verificação de tipo), `tool_calls` com validação de tipo, `content` vazio aceite, `argumentos` aceita `str` ou `dict`, `ServicoIndisponivelError` tratado no ciclo. Validação: 21 testes unitários offline passaram; smoke test real contra OpenRouter com `cohere/north-mini-code:free` criou evento com sucesso (ID 4). Sem alteração de BD.

**Versão v1.4.3** — fix de cache pós-deploy. As alterações CSS e a alternância de tema não chegavam aos utilizadores após deploy porque o Service Worker (`pipe-v2`) e o cache HTTP do Flask (12h) serviam ficheiros antigos. Corrigido com três alterações: (1) `app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0` em `app/__init__.py` para desactivar cache HTTP de ficheiros estáticos; (2) bumped do Service Worker para `CACHE = 'pipe-v3'` em `app/static/sw.js` (o `activate` handler já tinha `skipWaiting()` + `clients.claim()` para invalidar caches antigos); (3) cache-busting `?v=3` no link do CSS em `app/templates/base.html`. Sem alteração de BD.

**Versão v1.4.2** — nove módulos completos (oito deployed + Calendário local; mais o módulo **Combustíveis**, local). Módulo Calendário implementado com vistas Agenda e Mensal, CRUD completo via API, modal único, paleta de 11 cores e integração na Loja de Módulos. Módulo Combustíveis implementado com recolha via **API Aberta** (`api.apiaberta.pt/v1/fuel/stations`, autenticada com `X-API-Key`) para Braga/Vila Verde/Amares, dashboard filtrado, definições de concelhos+combustíveis e tarefa agendada às terças. Primeira recolha completa concluída com **95 postos** — mas via implementação DGEG; após o refactor para a API Aberta o bug de paginação (`return` dentro do `while`) limitava a recolha a 4 postos, corrigido em v1.3.1. Commit do fix `cf58e59` no branch `main` (publicado no GitHub). Em v1.4.0: tema claro/escuro concluído e testado — tokens semânticos no `pipe.css`, alternador 🌙/☀️ na navbar (persistido em `localStorage['pipe-tema']`, default escuro), anti-FOUC no `base.html` e service worker passado a network-first para CSS/JS/HTML (cache `pipe-v2`); sem migração de BD — o deploy exige apenas push + Reload no PA (na primeira visita ao browser, recarregar 2× para o SW novo activar). Em v1.4.1: paleta de cores do módulo Notas actualizada para a paleta Google Keep (8 cores vibrantes aplicáveis em tema claro e escuro, sem necessidade de migração de BD); sem novas rotas. Em v1.4.2: fix de contraste — texto em cartões de nota coloridos forçado a preto (`css .nota-com-cor` + fallback `var(--nota-texto, var(--cor-texto))` nas classes do editor `.nota-editar-titulo`/`.nota-editar-textarea`/`.checklist-editar-input`) em ambos os temas, evitando texto branco invisível sobre fundos claros; sem alteração de BD.

**Pendências do Calendário:**
- `tarefa_calendario_hoje()` em `pipe_tasks.py` — notificação de eventos do dia seguinte às 08:00
- Deploy no PythonAnywhere + migração da tabela `evento`
- **Backlog v1.x:** tela de detalhe do evento (read-only, acionada ao clicar no evento na Agenda ou Vista Mensal; botão "Editar" dentro do detalhe abre o modal existente)

**Pendências gerais:**
- **Assistente IA:** retry/fallback a melhorar (modelo e logging corrigidos em v1.4.0)
- **Módulos futuros:** arquitectura pronta — versão 1.x

---

## Próximos passos imediatos

1. Módulo Combustíveis — primeira recolha manual concluída ✅ (95 postos; as 1480 linhas existentes vieram da era DGEG — após a correcção v1.3.1 a recolha via API Aberta valida 80 postos por ciclo e o dedup impede linhas repetidas)
2. Deploy do módulo Combustíveis no PythonAnywhere + `db.create_all()` para criar as tabelas (funciona no primeiro reload, sem migração manual)
   - `api.apiaberta.pt` já está na whitelist do PA (documentação Swagger pública)
   - Definir `APIABERTA_API_KEY` no `.env` do PA e Reload da web app (sem a chave, 30 pedidos/min; com chave, 300/min — com o filtro `district` a recolha desceu de ~25 s para ~3-4 s)
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
