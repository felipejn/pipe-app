# PIPE — Estado Actual do Projecto — v1.7.2

## O que é o PIPE

Plataforma Inteligente Pessoal e Expansível — aplicação web Flask modular.
O nome é simultaneamente um acrónimo e o apelido do utilizador (Felipe = Pipe).
O módulo Euromilhões é o primeiro módulo, o módulo Tarefas é o segundo, o módulo Notas é o terceiro, o módulo Passwords é o quarto. O módulo Loja de Módulos é o sistema de personalização. O módulo Calendário é o oitavo módulo. O módulo Combustíveis é o nono módulo. O módulo Meteorologia é o décimo primeiro. A arquitectura suporta adição de novos módulos com a mesma identidade visual.

---

## Estrutura do projecto

```
pipe-app/
├── app/
│   ├── __init__.py          # create_app, app factory + security headers
│   ├── extensions.py        # Limiter (Flask-Limiter, X-Forwarded-For para PA)
│   ├── static/
│   │   ├── css/pipe.css     # design system (tema escuro + tema claro via tokens semânticos) + cores de eventos do Calendário + navegação secundária
│   │   ├── icons/           # icon-192.png, icon-512.png (PWA)
│   │   ├── manifest.json    # PWA — manifest
│   │   ├── sw.js            # PWA — service worker (network-first para CSS/JS/HTML, cache pipe-v3)
│   │   └── js/
│   │       └── pipe.js      # JS base (alertas + alternância de tema claro/escuro)
│   ├── templates/
│   │   ├── base.html        # navbar + alternador de tema 🌙/☀️ + anti-FOUC + barra secundária «Voltar/Home» (oculta no dashboard) + meta `csrf-token` (cofre/extensão)
│   │   ├── dashboard.html   # dashboard — grelha híbrida de cards com resumos por provider (Tarefas + Calendário); fallback clássico automático se não houver provider
│   │   ├── assistente/
│   │   │   └── index.html   # interface de chat do Assistente IA
│   │   ├── auth/            # login, registo (por convite), 2FA, reset password
│   │   ├── euromilhoes/     # registo de jogos e comparação com sorteios
│   │   ├── meteorologia/    # Previsão do tempo (Etapa A: localização; Etapa B: previsão Open-Meteo)
│   │   │   ├── index.html   # vista de previsão: local, temperatura, sensação, 24h + 7 dias
│   │   │   └── localizacao.html  # pesquisa e confirmação da localização geográfica
│   │   ├── tarefas/
│   │   │   ├── index.html   # vistas lista/detalhe + sidebar de tags
│   │   │   └── partials/    # items, form, sidebar
│   │   ├── notas/           # grelha de cartões, etiquetas, checklist
│   │   ├── passwords/       # gerador + cofre (desbloqueio) + exportação
│   │   ├── conversoes/      # conversor de ficheiros (HEIC→JPG, PNG/JPG→ICO)
│   │   ├── cambio/          # conversor de moedas (Wise v3 + fallback)
│   │   ├── cores/           # conversor HEX↔RGB↔HSL para Flutter
│   │   ├── modulos/
│   │   │   └── loja.html    # Loja de Módulos — ativar/desativar módulos
│   │   └── calendario/      # vista mensal + vista de agenda
│   ├── auth/                # Blueprint Auth
│   │   ├── __init__.py
│   │   ├── forms.py         # LoginForm, RegistoForm, 2FA, reset
│   │   ├── models.py        # User + Convite
│   │   └── routes.py        # /auth/*
│   ├── euromilhoes/         # Blueprint Euromilhões
│   │   ├── __init__.py
│   │   ├── models.py        # Jogo
│   │   └── routes.py        # /euromilhoes/
│   ├── tarefas/             # Blueprint Tarefas
│   │   ├── __init__.py
│   │   ├── models.py        # Lista, Tarefa, TagTarefa
│   │   ├── forms.py         # ListaForm, TarefaForm
│   │   ├── seed.py          # semear_listas_predefinidas (v1.5.7)
│   │   └── routes.py        # /tarefas/
│   ├── notas/               # Blueprint Notas
│   │   ├── __init__.py
│   │   ├── models.py        # Nota, ItemChecklist, EtiquetaNota
│   │   └── routes.py        # /notas/
│   ├── passwords/           # Blueprint Passwords (gerador + cofre)
│   │   ├── __init__.py
│   │   ├── crypto.py        # AES-256-GCM + PBKDF2-SHA256 (600 000 it.) + bcrypt da password mestra
│   │   ├── models.py        # CofreConfig, CofrePassword + extrair_dominio() (dedup por domínio)
│   │   ├── wordlist.py      # lista PT ~200 palavras para passphrases
│   │   ├── generator.py     # geração com secrets + cálculo de força por entropia
│   │   └── routes.py        # /passwords/ + /passwords/api/cofre/* + /passwords/api/csrf-token
│   ├── cambio/              # Blueprint Câmbio
│   │   ├── __init__.py
│   │   ├── service.py       # MOEDAS + obter_taxa (Wise v3 + fallback, partilhado com Assistente IA)
│   │   └── routes.py        # /cambio/ — stateless, delega no service.py
│   ├── cores/               # Blueprint Cores Flutter
│   │   ├── __init__.py
│   │   └── routes.py        # /cores/ — stateless, HEX/RGB/HSL/CMYK para Flutter
│   ├── conversoes/          # Blueprint Conversões
│   │   ├── __init__.py
│   │   ├── models.py        # modelo Conversao (histórico, sem ficheiros)
│   │   └── routes.py        # /conversoes/ — HEIC→JPG + PNG/JPG→ICO
│   ├── assistente/          # Blueprint Assistente IA
│   │   ├── __init__.py
│   │   ├── cliente.py       # OpenRouter API, retry + fallback entre modelos
│   │   ├── contexto.py      # orquestração do fluxo, histórico em sessão, tool use
│   │   ├── ferramentas.py   # 8 ferramentas de leitura + 10 de escrita
│   │   └── routes.py        # /assistente/ + /assistente/api/*
│   ├── modulos/             # Blueprint Loja de Módulos
│   │   ├── __init__.py
│   │   ├── models.py        # UserModulo
│   │   ├── routes.py        # /modulos/loja
│   │   └── config.py        # MODULOS_DISPONIVEIS (11 módulos: adicionado `meteorologia` na v1.7.0)
│   ├── dashboard/           # Camada de resumos por provider (v1.7.0)
│   │   ├── base.py          # Contrato: `Estado`, `Metrica`, `DashboardProvider` (ABC)
│   │   ├── registry.py      # Registry explícito de providers + `carregar_providers()` em `create_app()`
│   │   ├── calendario.py    # (registo) -> provider em `app/calendario/dashboard.py`
│   │   └── tarefas.py       # (registo) -> provider em `app/tarefas/dashboard.py`
│   ├── calendario/          # Blueprint Calendário
│   │   ├── __init__.py
│   │   ├── models.py        # Evento
│   │   └── routes.py        # /calendario/ + /calendario/api/eventos
│   ├── combustiveis/        # Blueprint Combustíveis
│   │   ├── __init__.py
│   │   ├── models.py        # 5 tabelas (postos, preços, utilizador_concelho, utilizador_combustivel, estado_atualizacao)
│   │   ├── routes.py        # /combustiveis/ (dashboard, concelhos, tipos de combustível, actualização)
│   │   └── services.py      # API Aberta (api.apiaberta.pt), obsolescência de postos, dedup
│   ├── notifications/       # Sistema de notificações
│   │   ├── __init__.py
│   │   ├── models.py        # UserNotificationPreferences
│   │   ├── service.py       # orquestração de canais (Telegram + Email)
│   │   └── channels/        # TelegramChannel, EmailChannel
│   └── admin/               # Blueprint de administração
│       ├── __init__.py
│       ├── decorators.py    # @admin_required
│       └── routes.py        # /admin/ — gestão de convites
├── chrome-extension/        # extensão Chrome MV3 do Cofre (com ícones)
│   ├── manifest.json        # MV3 — activeTab, storage, tabs; host_permissions <all_urls>
│   ├── background.js        # service worker — API do PIPE + captura (origem configurável)
│   ├── popup.html / popup.js # popup — estado, desbloquear, listar/copiar/actualizar
│   ├── content.js           # content script — captura apenas em forms de login (ignora o PIPE)
│   ├── icon48.png / icon128.png # ícones gerados por scripts/gerar_icones_extensao.py
│   └── README.md            # instalação, permissões e fluxo de uso
├── docs/
│   ├── guia-extensao-chrome.md    # guia passo a passo da extensão (instalar e usar)
│   └── historico/           # briefings e relatórios antigos
│       └── plano-cofre-passwords.md  # plano de correcção do Cofre
├── scripts/
│   ├── criar_admin.py
│   ├── promover_admin.py
│   ├── pipe_tasks.py            # única scheduled task do PythonAnywhere
│   ├── popular_combustiveis.py  # recolha manual de combustíveis (helper)
│   ├── remover_postos_ignorados.py  # limpeza dos postos em services.NOMES_IGNORADOS
│   ├── reset_postos_combustiveis.py  # reset das tabelas de postos/histórico (combustíveis)
│   ├── testar_assistente.py     # smoke test do Assistente IA contra a OpenRouter
│   ├── backup_bd.py             # cópia de segurança de instance/pipe.db (mantém as últimas 10)
│   ├── gerar_icones_extensao.py # gera icon48/icon128 da extensão Chrome (Pillow, sem Flask)
│   ├── verificar_mailjet.py     # estado real dos emails no Mailjet + `--apenas-hoje`
│   └── smoke_combustiveis.py    # smoke test da ferramenta get_combustiveis (Assistente IA)
├── tests/
│   ├── conftest.py              # guarda-civil: bloqueia `db.drop_all()` com BD de ficheiro (obrigatório create_app('testing'))
│   ├── conftest_utils.py        # helpers de fixture de app
│   ├── test_cofre.py            # 32 testes
│   ├── test_convites_email.py   # 14 testes
│   ├── test_pipe_tasks.py       # 13 testes (tarefa_tarefas + tarefa_calendario, mocks)
│   ├── test_tarefas_listas_predefinidas.py  # 3 testes
│   ├── test_extensao_js.py      # 1 teste
│   ├── test_extensao_distribuicao.py  # 8 testes
│   ├── test_isolamento_bd.py    # 1 teste
│   ├── test_assistente_cliente.py     # 13 testes
│   ├── test_assistente_combustiveis.py# 31 testes
│   ├── test_assistente_contexto.py    # 9 testes
│   ├── test_assistente_contexto_truncagem.py # 10 testes
│   ├── test_combustiveis_dedup.py     # 11 testes
│   └── smoke/                 # smoke tests (ex.: test smoke api de conversoes)
├── migrations/             # Flask-Migrate — revisão única de baseline 3b14f5bd26a5 (22 tabelas)
│   └── versions/           # 3b14f5bd26a5_baseline.py (create_table de tudo; sem if_not_exists)
├── .env.example
├── requirements.txt
└── README.md

```

---

## Módulos

### Módulo Auth (`app/auth/`)

- Registo por convite apenas — `Convite` com token único, validade de 7 dias e contador de usos (`convites_usados`)
- Login com `@login_required` (Flask-Login)
- 2FA: **Telegram, Email e TOTP** — métodos configuráveis e simultâneos (`UserNotificationPreferences`, `pyotp` + `qrcode`)
- Reset de password por email
- Rotas: `/auth/login`, `/auth/register`, `/auth/2fa/*`, `/auth/reset/*`
- Rotas críticas protegidas por rate limiting (`Flask-Limiter`); falhas de login registadas com `app.logger.warning` (username + IP)

### Módulo Euromilhões (`app/euromilhoes/`)

- Modelo `Jogo` — `jogos_euromilhoes` (numeros, estrelas, data_sorteio, filtrado por `user_id`)
- Interface de registo de combinações e visualização do histórico; cálculo do próximo sorteio

### Módulo Tarefas (`app/tarefas/`)

- Modelos: `Lista`, `Tarefa`, `TagTarefa`
- Formulários Flask-WTF (`ListaForm`, `TarefaForm`); semente de listas predefinidas (`tarefas.seed`)
- Vistas de lista e de detalhe com busca e filtros por etiquetas; apoio ao teclado (atalhos de navegação)
- Notificações: no dia do prazo e em todos os dias de atraso até conclusão

### Módulo Loja de Módulos (`app/modulos/`)

- Modelo `UserModulo` (`user_modulos`) — ativação/desativação de módulos por utilizador
- `MODULOS_DISPONIVEIS` em `app/modulos/config.py` com 11 módulos (Euromilhões, Tarefas, Notas, Passwords, Câmbio, Cores, Conversões, Assistente IA, Calendário, Combustíveis, Meteorologia)
- Rotas: `/modulos/loja` (loja), `/modulos/api/toggle` (AJAX `POST` com `request.get_json()`)

### Módulo Notas (`app/notas/`)

- Modelos: `Nota`, `ItemChecklist`, `EtiquetaNota`
- Cartões com 8 cores (paleta do Google Keep), fixar/arquivar, busca em tempo real, checklist inline e etiquetas

### Módulo Passwords (`app/passwords/`)

- **Gerador (stateless):** modos Password (8–64 chars), Passphrase (3–10 palavras PT), PIN (4–12 dígitos); barra de força por entropia; cópia para a área de transferência
- **Cofre (com BD — `cofre_configs`, `cofre_passwords`):** AES-256-GCM com chave derivada por PBKDF2-SHA256 (`COFRE_KDF_ITERATIONS`, 600 000) da password mestra (verificação por bcrypt); a chave existe apenas em sessão server-side (Flask-Session filesystem em `instance/flask_session/`) e nunca no cookie; expira ao fim de `COFRE_SESSION_TIMEOUT` (900 s), bloqueando apenas o cofre — a sessão de login mantém-se; entradas deduplicadas por domínio normalizado (`extrair_dominio()`, única fonte de verdade) + username; importação de CSV do Chrome; todas as queries filtradas por `user_id` (anti-IDOR)
- **API:** `/passwords/api/cofre/*` (estado, activar, desbloquear, bloquear, alterar-password, CRUD de entradas, importar-csv) e `GET /passwords/api/csrf-token`, que devolve o token CSRF assinado (usado pelo JS do cofre e pela extensão Chrome — nunca `session['csrf_token']`, que é o valor cru); CORS restrito por `COFRE_CORS_ORIGINS`
- **Extensão Chrome (MV3):** `chrome-extension/` — popup (estado, desbloquear, listar/preencher) e content script com heurística de captura (só forms de login); origem do servidor configurável em `chrome.storage.local.pipeOrigin` (default: PythonAnywhere)

### Módulo Câmbio (`app/cambio/`)

- `service.py`: constante `MOEDAS` e função `obter_taxa(origem, destino, valor)` — API Wise v3 + fallback ExchangeRate-API, stateless
- Rotas: `/cambio/` (interface de conversão), `/cambio/api/convert` (AJAX `POST` `request.get_json()`)

### Módulo Cores (`app/cores/`)

- Swatches Material Design; conversão HEX↔RGB↔HSL↔CMYK com output para código Flutter
- Rotas: `/cores/` + `/cores/api/convert`

### Módulo Conversões (`app/conversoes/`)

- HEIC→JPG (`pillow_heif`) e PNG/JPG→ICO (`PIL`)
- Limites: `MAX_FICHEIROS = 20`, `MAX_TAMANHO_MB = 10`, `MAX_TAMANHO_BYTES = 10 485 760`; ficheiros processados em memória (sem persistência), histórico em `conversoes`
- Rotas: `/conversoes/` + `/conversoes/api/convert`

### Módulo Calendário (`app/calendario/`)

- Modelo `Evento` (`evento`) — `user_id`, `titulo`, `data_inicio`, `data_fim`, `descricao`, `localizacao`, `dia_inteiro`, `cor`, `notificar`
- Rotas: `/calendario/` (vista mensal + agenda), `/calendario/api/eventos` (GET com filtros `inicio`/`fim`; POST com `request.get_json()` — criar evento), rate limit 60/min
- Vistas de calendário com navegação mensal/agenda, cores de evento (tomate → grafite, 11 classes `.evento-*`)
- **Esquema:** a tabela `evento` está coberta pela baseline do Flask-Migrate `3b14f5bd26a5` (v1.6.0) — não existe migração manual a executar no PythonAnywhere; o `db.create_all()` só corre em testes. Alterações futuras de esquema seguem o procedimento Flask-Migrate (ver «Procedimento de deploy no PythonAnywhere»)

### Módulo Combustíveis (`app/combustiveis/`)

- Modelos: `combustiveis_postos`, `combustiveis_precos_historico`, `combustiveis_utilizador_concelho`, `combustiveis_utilizador_combustivel`, `combustiveis_estado_atualizacao` — FK de utilizador apontam para `utilizadores.id`; as 5 tabelas estão cobertas pela baseline `3b14f5bd26a5` (v1.6.0) — o `db.create_all()` só corre em testes
- `services.py`: recolha via API Aberta (`api.apiaberta.pt`) com paginação por tipo de combustível; arquivamento automático de postos ausentes (`LIMIAR_CICLOS_AUSENTE = 2` ciclos); dedup conservadora por `nome+morada+concelho` (`obter_ids_duplicados`) com exclusão apenas em leitura; blocklist `NOMES_IGNORADOS`
- Rotas: `/combustiveis/` (dashboard + `POST /combustiveis/atualizar`, rate limit 6/hora), `/combustiveis/concelhos`, `/combustiveis/tipos`
- Scripts auxiliares: `reset_postos_combustiveis.py` (drop + `db.create_all()` + repovoamento; cria colunas `ativo`/`ciclos_ausente` que o `create_all()` não acrescenta a uma BD existente), `remover_postos_ignorados.py` (idempotente), `popular_combustiveis.py` (recolha manual) — os dois primeiros são **históricos/obsoletos** desde a v1.6.0 (o baseline cobre o schema); não executar (ver «Armadilhas conhecidas»)
### Módulo Meteorologia (`app/meteorologia/`)

- Previsão do tempo em tempo real, com **Open-Meteo** (APIs de geocoding + forecast públicas, sem chave de API).
- **Etapa A — Localização:** modelo `LocalizacaoMeteorologia` (`meteorologia_localizacao`): `user_id` (FK, único), `nome`, `latitude`, `longitude`, `pais`, `regiao`, `timezone` (default `Europe/Lisbon`), `atualizada_em`; **1 localização por utilizador**; pesquisa por localidade com normalização (aceita "Gerês, Braga" para desambiguar) e confirmação.
- **Etapa B — Previsão:** `services.py` com funções puras `pesquisar_locais`, `guardar_localizacao`, `obter_previsao`, `obter_previsao_utilizador`; payload devolve `atual` (12 campos: temperatura, sensação térmica, humidade, precipitação, probabilidade de precipitação, código WMO, vento (velocidade + direção + ponto cardeal), UV, máx/mín do dia), `horaria` (próximas 24h) e `diaria` (próximos 7 dias); mapeamento WMO → descrição PT + emoji.
- **Resiliência:** API indisponível/timeout → mensagem amigável (200, nunca 500); campos ausentes → "—"; sem localização guardada → estado vazio com botão "Definir localização"; `timeout=8`s + `User-Agent` próprio (`PIPE-Meteorologia/1.0`).
- **Rotas:** `GET /meteorologia/` (previsão), `GET /meteorologia/localizacao` (Etapa A), `GET /meteorologia/api/pesquisar?q=` (rate limit 30/min), `POST /meteorologia/api/localizacao` (rate limit 10/min) — todas `@login_required`, filtradas por `user_id` (anti-IDOR).
- **Template:** server-side puro (Jinja) em `app/templates/meteorologia/` — previsão renderizada no servidor; AJAX com `'X-CSRFToken'` só na pesquisa/gravação da localização. Design com tokens claro/escuro, cards e botões no padrão PIPE.
- **Esquema:** migração `c420a200f2f2` (baseline `3b14f5bd26a5` → `c420a200f2f2`, criada com Flask-Migrate) — adiciona a tabela `meteorologia_localizacao`; aplicar no PythonAnywhere antes de abrir o módulo.
- **Testes:** `tests/test_meteorologia.py` (36 testes).

### Assistente IA (`app/assistente/`)

- **Cliente** (`cliente.py`): `chamar_llm(mensagens, ferramentas=None)` — HTTP POST para `openrouter.ai/api/v1/chat/completions`. Modelo principal via `OPENROUTER_MODEL` (default: `inclusionai/ling-3.0-flash-sante:free`) — **5 modelos no total (1 principal + 4 fallbacks)**. Fila de fallback: `poolside/laguna-s-2.1:free`, `liquid/lfm-2.5-2.6b:free`, `nvidia/nemotron-3-super-120b-a12b:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`. Auth por `OPENROUTER_API_KEY`; retry com backoff (3 tentativas: 2s, 5s, 10s) + fallback imediato em qualquer falha de provider (incluindo respostas HTTP 200 com `{"error": ...}` no corpo — detetadas por `_classificar_resposta()`, com classes `RateLimitError`/`ServicoIndisponivelError`)
- **Contexto** (`contexto.py`): `processar_mensagem_assistente(mensagem_utilizador, user_id, historico=None)` — orquestra o fluxo: monta prompt + histórico, chama LLM, executa tool calls (máx. 4 iterações), guarda resposta. Histórico em Flask session (20 mensagens = 10 trocas, tecto de 3000 chars/mensagem e 8000 chars no total)
- **Ferramentas** (`ferramentas.py`): tool use com **8 funções de leitura** (`get_tarefas`, `get_notas`, `get_euromilhoes`, `get_resumo_geral`, `get_eventos`, `get_cambio`, `get_combustiveis`, `get_meteorologia`) e **10 de escrita** (`criar_tarefa`, `alternar_tarefa`, `apagar_tarefa`, `criar_nota`, `alternar_nota_acao`, `apagar_nota`, `criar_evento`, `atualizar_evento`, `apagar_evento`, `gerar_credencial`). Todas filtram por `user_id` (obrigatório, injetado pelo caller); `get_combustiveis` aceita `tipo_combustivel`, `concelho`, `posto` (nome **ou** marca, insensível a acentos e maiúsculas), `apenas_mais_barato` e `limite`; `get_meteorologia` recebe `detalhado` (bool) e consulta a previsão da localização guardada em Meteorologia
- **Rotas** (`routes.py`):
  - `GET /assistente` — página de chat (tema claro/escuro)
  - `POST /assistente/api/chat` — AJAX `{mensagem: "..."}` → `{resposta: "..."}` (rate limit 30/min)
  - `POST /assistente/api/modo` — alterna modo leitura/escrita (rate limit 10/min)
  - `POST /assistente/api/limpar` — limpa histórico da sessão (rate limit 10/min)
- **System prompt:** PT-PT; capacidades limitadas à leitura em modo leitura (não sugere acções que não pode executar — encaminha para o módulo respectivo); nunca inventar dados; tom formal e conciso
- Testes: `test_assistente_cliente.py` (13), `test_assistente_combustiveis.py` (31), `test_assistente_contexto.py` (9), `test_assistente_contexto_truncagem.py` (10), `test_assistente_meteorologia.py` (14)

### Sistema de notificações (`app/notifications/`)

- Modelo `UserNotificationPreferences` (`notificacao_preferencias`) — preferências por canal (Telegram, Email, Tarefas, Calendário)
- `service.py` orquestra o envio; canais: `TelegramChannel` (python-telegram-bot) e `EmailChannel` (Mailjet)

### Scheduled task (`scripts/pipe_tasks.py`)

- Única scheduled task do PythonAnywhere: `python /home/felipejn/pipe-app/scripts/pipe_tasks.py`
- Configuração: comando acima, **hora 07:00**, recorrência diária
- Módulos activos:
  | Tarefa | Frequência | Descrição |
  |---|---|---|
  | `tarefa_euromilhoes` | Terças e sextas | Verifica resultados dos sorteios |
  | `tarefa_tarefas` | Todos os dias | Notifica tarefas com prazo para hoje («Vencem hoje») e em atraso — 1×/dia enquanto persistirem |
  | `tarefa_combustiveis` | Terças-feiras | Actualiza preços dos postos (via API Aberta), respeitando o intervalo mínimo de 1x/dia por terça |
  | `tarefa_calendario` | Todos os dias | Lembretes de eventos no dia anterior («Amanhã») e no dia («Hoje»); ignora eventos já iniciados e respeita o toggle `notificar` |

### Autenticação 2FA

- Telegram, Email, TOTP (`pyotp` + `qrcode`)
- Múltiplos métodos em simultâneo — utilizador escolhe no login

### Design System (`app/static/css/pipe.css`)

- Tema escuro (por defeito) e tema claro — acentos âmbar/dourado mantêm-se nos dois
- **Tokens semânticos em `:root`:** superfícies, bordas, texto, estados, prioridades, `--cor-overlay-hover`, `--sombra` — ~23 cores fixas substituídas por variáveis
- **Tema claro via `[data-theme="light"]`** — sobrepõe apenas os tokens; o `data-theme` é definido no `<html>` antes do CSS (script anti-FOUC no `base.html`)
- Cores de identidade preservadas nos dois temas: âmbar (`--cor-primaria`), 11 classes `.evento-*` do Calendário, bolas do Euromilhões, `#1a1000` sobre âmbar no `.btn-primario`
- Componentes: navbar, cartões, formulários, botões, alertas, skeleton loader, toggles, modais
- Componentes Euromilhões: bolas, barras de frequência, badges de resultado
- Componentes Tarefas: sidebar, items, check circular, busca, badges, estado vazio, selector mobile
- Componentes Notas: grelha de cartões, palete de cores, checklist, sidebar de etiquetas, 8 cores alinhadas à paleta Google Keep
- Componentes Combustíveis: dashboard de preços, grelha de postos, selector de concelho/tipo, badge de última actualização
- Componentes Assistente IA: balões de chat (`chat-bubble`, `--user` âmbar, `--assistant` `#2a2f47`/`#2b3149`), faixa lateral âmbar nos balões do assistente, classes `cartao-novo` + `badge-novo` para destaque de módulos no dashboard
- Componentes Calendário: 11 cores de evento (`.evento-tomate` … `.evento-grafite`)

### Interface / Navegação (frontend)

- **Dashboard** — grelha híbrida de cartões dos módulos activos; lida com `MODULOS_DISPONIVEIS` e, para cada módulo activo, consulta o provider correspondente em `app/dashboard/registry.py` e exibe um resumo de métricas (`resumo` de Tarefas e Calendário na v1.7.0 — quando há dados: contagens como "3 Pendentes", "12 Total"; sem dados: card fica só com ícone + nome). O **badge de estado foi removido** — os três estados (`ok` / `nao_configurado` / `indisponivel`) mantêm-se a ser calculados internamente pelos providers, mas deixam de ser exibidos porque são redundantes: a própria presença das contagens confirma que o módulo está activo. Módulos sem provider ficam no layout clássico; renderização 100 % SQL local, sem HTTP externo. Card clássico com fallback automático (sem parâmetro `resumos`) — regressão zero.
- **Padrão AJAX/fetch no PIPE:**
  - Passar sempre `'X-CSRFToken': '{{ csrf_token() }}'` no header do fetch
  - Backend usa `request.get_json()` — não usa `validate_on_submit()`
- **Padrão de imports nos blueprints:**
  - `from app import db` — para SQLAlchemy
  - `from app.extensions import limiter` — para rate limiting

---

## Segurança

| Medida | Implementação | Ficheiro |
|---|---|---|
| CSRF | Flask-WTF CSRFProtect em todos os formulários | `app/__init__.py` |
| Rate limiting | Flask-Limiter nas rotas críticas | `app/auth/routes.py`, `app/combustiveis/routes.py`, `app/assistente/routes.py`, `app/extensions.py` |
| Logging de login falhado | `app.logger.warning` com username e IP | `app/auth/routes.py` |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | `app/__init__.py` |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` | `app/auth/models.py` |
| Controlo de acesso | `@login_required` e `@admin_required` | rotas protegidas |
| Configuração IP PA | `X-Forwarded-For` no Limiter | `app/extensions.py` |
| CORS do cofre | `COFRE_CORS_ORIGINS` (apenas `chrome-extension://<ID>`): origem autorizada recebe `Access-Control-Allow-Origin` + `Allow-Credentials`; origem errada não recebe o header | `app/__init__.py`, `config.py` |
| Cookie de sessão cross-site (extensão Chrome) | `SameSite=None` + `Secure` em produção (obrigatório para os `fetch` a partir de `chrome-extension://`); `Lax` em desenvolvimento | `config.py`, `app/__init__.py` |
| Sessão do cofre | chave AES só em Flask-Session server-side (`instance/flask_session/`); expira em `COFRE_SESSION_TIMEOUT` (900 s), bloqueando apenas o cofre | `app/passwords/routes.py` |

---

## Testes

- Execução:
  - `pytest --collect-only -q` — recolhe todos os testes (182 colectados)
  - `pytest -q` — executa a suite completa
- A suite consta de 17 ficheiros de teste, totalizando **210 testes**: `test_cofre.py` (32), `test_convites_email.py` (14), `test_pipe_tasks.py` (13), `test_assistente_combustiveis.py` (31), `test_assistente_cliente.py` (13), `test_combustiveis_dedup.py` (11), `test_assistente_contexto_truncagem.py` (10), `test_assistente_contexto.py` (9), `test_assistente_meteorologia.py` (14), `test_extensao_distribuicao.py` (8), `test_tarefas_listas_predefinidas.py` (3), `test_extensao_js.py` (1), `test_isolamento_bd.py` (1), `test_dashboard.py` (14) + `test_meteorologia.py` (36) e helpers em `conftest.py`/`conftest_utils.py`
- **Aviso do `conftest.py`:** nenhum teste pode tocar na BD real do PIPE. O `drop_all_seguro` intercepta `flask_sqlalchemy.SQLAlchemy.drop_all` e levanta `RuntimeError` sempre que a URI da BD não for `:memory:` — obrigatoriedade de criar a app com `create_app('testing')` (SQLite em memória + sessões em pasta temporária). O anti-padrão `db.drop_all()` com BD de ficheiro levanta erro porque o engine do SQLAlchemy fica fixado em `db.init_app()` e a reatribuição de `SQLALCHEMY_DATABASE_URI` depois de `create_app()` não tem efeito

---

## Deploy no PythonAnywhere

### Estado

- **App online** em `https://felipejn.pythonanywhere.com` ✅
- **WSGI configurado** ✅
- **Static files** configurados ✅
- **Scheduled task** — `python /home/felipejn/pipe-app/scripts/pipe_tasks.py` às **07:00** ✅ (configuração confirmada no painel Tasks do PythonAnywhere)
- **Flask-Migrate — baseline `3b14f5bd26a5`** ✅: a produção foi **stamped** para `3b14f5bd26a5` em 2026-10-06 (a baseline **não** foi executada sobre os dados existentes — o esquema em produção já continha todas as tabelas e colunas); confirmar com `flask db current` (produção: `3b14f5bd26a5 (head)`; depois do deploy do Meteorologia: `c420a200f2f2 (head)`) e `flask db check` (limpo).
- **Esquema (Calendário, Cofre, Combustíveis, Convites/Mailjet)** ✅ — resolvido pela baseline: `evento`, `cofre_configs`/`cofre_passwords`, as colunas `ativo`/`ciclos_ausente` e `mailjet_message_id`/`email_estado`/`email_verificado_em` já existiam em produção e estão cobertas por `3b14f5bd26a5`; a correcção de `User.is_admin` (`nullable=False`, `server_default=0`) também está integrada na baseline — **nenhum script manual de migração é necessário nem recomendado**
- **Configuração de produção** (pacotes via `pip install -r requirements.txt`, variáveis do `.env` como `COFRE_CORS_ORIGINS`, cookies `SameSite=None`/`Secure`) — não é verificável a partir do repositório; confirmar no painel/terminal do PythonAnywhere se ainda não foi feito
- **Extensão Chrome do Cofre** ⚠️: teste de ponta a ponta em produção pendente (ver «Pendências de deploy»)

### Migrations (Flask-Migrate)

A baseline `3b14f5bd26a5` cobre todas as tabelas e colunas actuais (incluindo `evento`); **exceto a migração pendente `c420a200f2f2` (Meteorologia)**; no PythonAnywhere não há outros comandos manuais de migração a executar. Novas alterações de esquema seguem o procedimento descrito em «Procedimento de deploy no PythonAnywhere».
- **Migração pendente — Meteorologia (`c420a200f2f2_adiciona_meteorologia_localizacao.py`):** aplica a tabela `meteorologia_localizacao` (Etapa A: uma localização por utilizador) antes de usar o módulo; executar `flask db upgrade` no PythonAnywhere, depois confirmar `flask db current` (deve indicar `c420a200f2f2 (head)`) e `flask db check` (limpo).


### WSGI

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
COFRE_CORS_ORIGINS=chrome-extension://<ID da extensão>
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=inclusionai/ling-3.0-flash-sante:free
```

### Cópia de segurança da BD

`python scripts/backup_bd.py` copia `instance/pipe.db` para `instance/backups/pipe-AAAAMMDD-HHMMSS.db` (mantém as últimas 10). Correr antes de operações de risco (reset de tabelas, migrações manuais).

---

## Pendências de deploy
- **Módulo Meteorologia (deploy em pendência):** aplicar a migration `c420a200f2f2_adiciona_meteorologia_localizacao.py` (`flask db upgrade`) antes de usar o módulo; depois confirmar com `flask db current` (`c420a200f2f2 (head)`) e `flask db check` (limpo).

- **Calendário, Cofre, Combustíveis, Convites/Mailjet** — ✅ **resolvido pela baseline do Flask-Migrate** (`3b14f5bd26a5`, stamped no PA em 2026-10-06); os scripts manuais (`migrar_convites_mailjet.py`, `reset_postos_combustiveis.py`, `remover_postos_ignorados.py`) são históricos e **não devem ser executados**
- **Extensão Chrome do Cofre:** teste de ponta a ponta em produção seguindo `docs/guia-extensao-chrome.md` (login no PIPE → desbloquear cofre → visitar site com login guardado → preencher); confirmar CORS e que a chave do cofre não aparece nos cookies; recarregar ⟳ o cartão da extensão em `chrome://extensions` depois das alterações
- ⚠️ **Antes de qualquer operação de risco sobre a BD (ex.: `flask db upgrade`), correr:** `python scripts/backup_bd.py` e descarregar a cópia para a máquina local

---

## Procedimento de deploy no PythonAnywhere

### Deploy sem mudança de esquema (maioria dos deploys)

1. `python scripts/backup_bd.py` (recomendado)
2. `git pull`
3. `pip install -r requirements.txt`
4. Reload da aplicação
5. `flask db check` — deve continuar a devolver "No new upgrade operations detected."

### Alterações de esquema (Flask-Migrate)

A baseline `3b14f5bd26a5` é **imutável**: nunca editar nem reescrever migrations antigas; alterações futuras criam **novas revisions** a partir dela.

**Adopção inicial da baseline (já executada em 2026-10-06):**
`flask db check` → `flask db stamp 3b14f5bd26a5`

O `stamp` foi usado apenas uma vez, para registar que a BD de produção já correspondia ao esquema da baseline (a baseline não foi executada sobre os dados existentes). **Não** é o procedimento normal para futuras migrations.

**Fluxo normal para futuras alterações de schema:**

1. Alterar os modelos em `app/<módulo>/models.py`
2. `flask db migrate -m "descrição"` (em ambiente local)
3. Rever o diff da migration gerada em `migrations/versions/`
4. Testar (`pytest -q`) e validar o `flask db upgrade` numa BD vazia, se aplicável
5. `python scripts/backup_bd.py` **e descarregar a cópia** de `instance/backups/` para a máquina local
6. No PythonAnywhere: `git pull` → `pip install -r requirements.txt` → `flask db upgrade`
7. Confirmar com `flask db current` (revisão esperada) e `flask db check` (limpo)
8. Reload da aplicação

### Restauro de backup

Com a **app parada**, copiar o ficheiro mais recente de `instance/backups/` para `instance/pipe.db` e arrancar a app.

---

## Armadilhas conhecidas

- **`create_all()` só corre em testes (v1.6.0)** — nunca altera uma BD existente (não faz `ALTER TABLE`); o esquema evolui com Flask-Migrate: alterar o modelo → `flask db migrate -m "..."` → rever o diff → `python scripts/backup_bd.py` → `flask db upgrade`. BD local perdida ou para recriar de zero: `del instance\pipe.db` → `flask db upgrade` → `python scripts/criar_admin.py`
- **Scripts de migração manuais são históricos** — `scripts/migrar_convites_mailjet.py` (e outros `migrar_*.py`) e `scripts/reset_postos_combustiveis.py` estão **OBSOLETOS** desde a v1.6.0 (o baseline do Flask-Migrate cobre o schema); ficam só como documentação — **NÃO alterar os scripts**
- **Engine fixado em `db.init_app()`** — atribuir `app.config['SQLALCHEMY_DATABASE_URI']` **depois** de `create_app()` não tem efeito sobre o engine já construído; por isso os testes têm de usar `create_app('testing')` antes de qualquer reatribuição (o conftest bloqueia `db.drop_all()` com BD de ficheiro)
- **Cache do nginx do PythonAnywhere** — serve ficheiros estáticos com cache de longo prazo e **ignora parâmetros de query**; quando se altera o CSS é preciso actualizar o `cache-buster` em `base.html` (`?v=...`) para forçar o reload no browser
- **OpenRouter pode devolver HTTP 200 com erro** — quando o provider upstream falha, o corpo é `{"error": ...}`; o código do Assistente IA deve usar `_classificar_resposta()` em vez de confiar só em `raise_for_status()`; há fila de fallback de modelos gratuitos
- **`db` não está em `app.extensions`** — o objeto SQLAlchemy vive em `app/__init__.py` (importar via `from app import db`)

---

## Arquitectura de módulos

1. Criar `app/<modulo>/` com `__init__.py` + `routes.py` (+ `models.py` se BD)
2. Registar blueprint em `app/__init__.py`
3. Adicionar entrada em `app/modulos/config.py` (`MODULOS_DISPONIVEIS`) — o card aparece **automaticamente** na dashboard (layout híbrido de v1.7.0, sem editar `dashboard.html`)
4. Se o módulo quiser um resumo no dashboard (como Tarefas/Calendário): implementar provider em `app/<modulo>/dashboard.py` e registá-lo em `app/dashboard/registry.py::carregar_providers()`
5. Se precisa de scheduled task: adicionar em `scripts/pipe_tasks.py`

Padrões: AJAX via `'X-CSRFToken': '{{ csrf_token() }}'` + `request.get_json()`; imports `from app import db` e `from app.extensions import limiter`; rate limiting nas rotas críticas; tudo filtrado por `user_id` (anti-IDOR), exceto os `Posto` do Combustíveis que são globais.

---

## Próximos passos

1. **Deploy do módulo Meteorologia no PythonAnywhere:** `git pull` → `flask db upgrade` (aplica a migration `c420a200f2f2_adiciona_meteorologia_localizacao.py`) → check `flask db current`/`flask db check` → **Reload**; verificar a previsão com Open-Meteo real.
2. **Testar notificações do Calendário em produção** — via `pipe_tasks.py` (tarefa `tarefa_calendario`).
3. **Testar o dashboard com resumos em produção** — confirmar badges de estado e métricas de Tarefas/Calendário; depois expandir os providers (Combustíveis, Notas, Euromilhões, Passwords) conforme o plano `docs/plano_dash_global_v1.7.0.md`.
4. **Extensão Chrome do Cofre** — teste de ponta a ponta em produção.
5. **Futuras alterações de schema** — seguir o procedimento Flask-Migrate (nunca editar a baseline `3b14f5bd26a5`).
6. Manter `CHANGELOG.md` atualizado com cada versão — o histórico do projecto vive apenas lá a partir de agora.

---

## Dependências

- Flask 3.0, Flask-Login, Flask-WTF, Flask-SQLAlchemy, Flask-Limiter, Flask-Session
- Werkzeug, SQLAlchemy, python-dotenv
- pyotp, qrcode
- requests, python-telegram-bot
- Pillow, pillow_heif
- cryptography, bcrypt, flask-cors

## Contexto técnico

- Deploy em PythonAnywhere (plano free) por trás do nginx; base de dados SQLite em `instance/pipe.db`
- Modelo app factory: `create_app(config_name)` com ambiente `testing` para testes (SQLite em memória)
- Frontend vanilla JS inline nos templates; sem ficheiros JS externos por módulo
- PWA: `manifest.json` + `sw.js` (service worker, cache `pipe-v3`)
- Autenticação de dois fatores via Telegram, email e TOTP; convites com validade de 7 dias para registo

---

**Histórico de versões: ver [CHANGELOG.md](CHANGELOG.md)**
