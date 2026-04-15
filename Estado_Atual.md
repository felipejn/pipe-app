# PIPE — Estado Actual do Projecto — v1.1

## O que é o PIPE
Plataforma Inteligente Pessoal e Expansível — aplicação web Flask modular.
O nome é simultaneamente um acrónimo e o apelido do utilizador (Felipe = Pipe).
O módulo Euromilhões é o primeiro módulo, o módulo Tarefas é o segundo, o módulo Notas é o terceiro, o módulo Passwords é o quarto. A arquitectura suporta adição de novos módulos com a mesma identidade visual. O módulo Loja de Módulos é o sistema de personalização, permitindo a cada utilizador activar/desactivar módulos independentemente.

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
│   │   ├── css/pipe.css     # design system (tema escuro, âmbar/dourado)
│   │   └── js/
│   │       ├── pipe.js      # JS base (alertas)
│   │       └── passwords.js # JS do módulo Passwords (não utilizado — JS inline no template)
│   ├── templates/
│   │   ├── base.html        # navbar sem links de módulos (navegação via dashboard)
│   │   ├── dashboard.html   # cards de módulos: Euromilhões + Tarefas + Notas + Passwords + Câmbio
│   │   ├── auth/
│   │   ├── euromilhoes/
│   │   ├── settings/
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── decorators.py    # @admin_required
│   │   │   ├── routes.py        # /admin/ — incluindo gestão de convites
│   │   │   └── templates/
│   │   │       ├── dashboard.html
│   │   │       ├── utilizadores.html
│   │   │       └── convites.html   # gestão de convites (AJAX)
│   │   ├── tarefas/
│   │   │   ├── index.html
│   │   │   ├── editar.html
│   │   │   └── _tarefa.html
│   │   ├── notas/
│   │   │   ├── index.html
│   │   │   ├── editar.html
│   │   │   └── _cartao.html
│   │   └── passwords/
│   │       └── index.html
│   │   └── cambio/
│   │       └── index.html
│   │   └── modulos/
│   │       └── loja.html
│   └── conversoes/
│       ├── __init__.py
│       ├── models.py        # modelo Conversao (histórico, sem ficheiros)
│       └── routes.py        # /conversoes/ — HEIC→JPG + PNG/JPG→ICO
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
│   │       └── email.py     # EmailChannel (SendGrid)
│   ├── settings/            # Blueprint de definições
│   │   ├── __init__.py
│   │   └── routes.py        # /definicoes/
│   ├── admin/               # Blueprint de administração
│   │   ├── __init__.py
│   │   ├── decorators.py    # @admin_required
│   │   └── routes.py        # /admin/
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
│   └── cores/               # Blueprint Cores Flutter
│       ├── __init__.py
│       └── routes.py        # /cores/ — stateless, HEX/RGB/HSL/CMYK para Flutter
│   ├── modulos/             # Blueprint Loja de Módulos
│   │   ├── __init__.py
│   │   ├── config.py        # MODULOS_DISPONIVEIS
│   │   ├── models.py        # UserModulo
│   │   └── routes.py        # /modulos/loja, /modulos/api/toggle
│   ├── assistente/          # Blueprint Assistente IA
│   │   ├── __init__.py
│   │   ├── cliente.py       # OpenRouter API
│   │   ├── contexto.py      # tool use orchestration
│   │   ├── ferramentas.py   # tool functions
│   │   └── routes.py        # /assistente
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

### Módulo Auth (`app/auth/`)
- Modelo `User` com password em hash (Werkzeug)
- Campo `is_admin` — Boolean, default=False
- Novo modelo `Convite` — sistema de registo por convite (único, 7 dias de validade)
- Formulários: `LoginForm`, `RegistoForm`, `AlterarPasswordForm`, `VerificarCodigoForm`, `ConfigurarDoisFAForm`, `ConfirmarTOTPForm`, `PedirResetForm`, `ResetPasswordForm`
- Rotas: `/auth/login`, `/auth/registo` (bloqueado — requer convite), `/auth/registo/<token>` (criação de conta via link de convite), `/auth/logout`, `/auth/perfil`
- Rotas 2FA: `/auth/2fa/verificar`, `/auth/2fa/escolher`, `/auth/2fa/enviar/<metodo>`, `/auth/2fa/reenviar`
- Rotas TOTP: `/auth/2fa/totp/configurar`, `/auth/2fa/totp/desactivar`
- Rotas recuperação de password: `/auth/recuperar-password`, `/auth/reset-password/<token>`
- Templates: `login.html`, `registo_token.html` (registo com convite), `perfil.html`, e 2FA
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
- **Comportamento ao abrir:** vista "Todas" por defeito (`lista='todas'`) — parâmetro `lista` tem default `'todas'` em `routes.py`
- **Mobile:** selector `<select>` acima da grelha, visível apenas em ecrãs ≤ 640px; em desktop a sidebar continua a funcionar normalmente

### Módulo Loja de Módulos (`app/modulos/`)
- Sem BD própria — usa tabela `UserModulo` (`user_id` + `modulo_slug` + `ativo`)
- `config.py` — dicionário `MODULOS_DISPONIVEIS` com 8 módulos (`slug`, `nome`, `icone`, `url_endpoint`, `descricao`)
- `models.py` — modelo `UserModulo` (PK composta) + helper `get_modulos_ativos(user_id)`
- `routes.py` — `GET /modulos/loja`, `POST /modulos/api/toggle` (AJAX + CSRF)
- Ícone 🛒 na navbar acessível a todos os utilizadores autenticados
- Zero módulos activos por defeito — dashboard mostra estado vazio com link para a loja
- Cards com toggle switch + label 'Instalar'/'Instalado' com feedback visual

### Módulo Notas (`app/notas/`)
- **Modelos:**
  - `Nota` — texto livre ou checklist, cor de fundo, fixada, arquivada
  - `ItemChecklist` — itens de notas do tipo checklist (ordem, feito)
  - `EtiquetaNota` — etiquetas reutilizáveis, many-to-many com Nota
- **Rotas:**
  - `GET /notas/` — grelha de cartões (`?busca=`, `?etiqueta=`, `?arquivo=1`)
  - `POST /notas/criar` — criar nota via AJAX (JSON)
  - `GET/POST /notas/<id>` — editar nota (página completa)
  - `POST /notas/<id>/accao` — fixar, arquivar, cor, toggle_item (JSON)
  - `POST /notas/<id>/apagar` — apagar nota definitivamente
- **Funcionalidades:**
  - Grelha de cartões com criação inline sem mudar de página
  - Suporte a texto livre e checklist
  - 8 cores de fundo dentro do tema escuro
  - Fixar no topo / arquivar (em vez de apagar)
  - Etiquetas com sugestão automática na edição
  - Busca em tempo real por título, corpo e etiquetas
  - Toggle de itens de checklist directamente no cartão
  - Navegação por clique em qualquer zona do cartão
  - Sidebar com etiquetas e acesso ao arquivo
  - Botão Arquivar/Recuperar consoante o estado da nota

### Módulo Passwords (`app/passwords/`)
- **Sem BD** — módulo totalmente stateless, sem modelos nem migrações
- **Ficheiros:**
  - `wordlist.py` — lista PT com ~200 palavras para geração de passphrases
  - `generator.py` — geração criptograficamente segura com `secrets` + cálculo de força por entropia
- **Rotas:**
  - `GET /passwords/` — página do gerador
  - `POST /passwords/api/gerar` — API JSON (requer `X-CSRFToken` no header)
- **Modos:**
  - **Password** — comprimento 8–64, toggles: maiúsculas, minúsculas, números, símbolos, excluir ambíguos
  - **Passphrase** — 3–10 palavras PT separadas por hífen
  - **PIN** — 4–12 dígitos numéricos
- **Funcionalidades:**
  - Tabs para alternar entre os três modos
  - Barra de força com 5 níveis calculados por entropia no backend
  - Botão Copiar com feedback visual ("Copiado!")
  - Gera automaticamente ao carregar a página e ao mover sliders/toggles
  - Frontend vanilla JS inline no template — sem ficheiros JS externos
  - CSRF: token passado via `X-CSRFToken` no header do fetch (padrão do PIPE)

### Módulo Câmbio (`app/cambio/`)
- **Sem BD** — módulo stateless, sem modelos nem migrações
- **Rotas:**
  - `GET /cambio/` — página de conversão
  - `POST /cambio/api/convert` — API JSON (requer `X-CSRFToken` no header)
- **API externa:** Wise API v3 (`/v3/quotes`) com fallback para ExchangeRate-API
  - Seleciona opção de pagamento DEBIT (corresponde ao valor apresentado no site da Wise)
  - Extrai fees detalhados: `fee.total`, `price.items` (fee pagamento, comissão Wise, IOF tax)
- **Moedas:** EUR, BRL, USD, GBP, JPY, CHF, CAD, AUD
- **Funcionalidades:**
  - Default EUR → BRL, selects configáveis para qualquer par
  - Resultado formatado com `Intl.NumberFormat` por moeda (locale + currency corretos)
  - Botão de inverter moedas entre os selects (troca origem/destino e reconverte automaticamente)
  - Secção de taxas Wise exibida quando disponível: total das fees + discriminação individual
  - Conversão automática ao trocar moedas, inverter moedas ou carregar o botão
  - Botão Copiar com feedback visual
  - Frontend vanilla JS inline no template — sem ficheiros JS externos

### Módulo Cores (`app/cores/`)
- **Sem BD** — módulo stateless, sem modelos nem migrações
- **Rotas:**
  - `GET /cores/` — página com color picker e tabs
  - `POST /cores/api/convert` — API JSON (requer `X-CSRFToken` no header)
- **Funcionalidades:**
  - **Cor → Flutter**: color picker visual + input em HEX, RGB, HSL ou CMYK
  - **Flutter → Cor**: cola código Flutter (`Color(0x..)`) → mostra cor e equivalentes
  - Gera todos os equivalentes: `Color(0x..)`, `Color.fromRGBO`, `Color.fromARGB`, `HSLColor.fromAHSL`, `HSVColor.fromAHSV`, swatch Material mais próximo, CSS
  - Botão Copiar em cada linha de código
  - Preview visual da cor em tempo real

### Módulo Conversões (`app/conversoes/`)
- **Modelos:**
  - `Conversao` — metadados no histórico (sem ficheiros armazenados)
- **Rotas:**
  - `GET /conversoes/` — dropzone + histórico recente
  - `POST /conversoes/api/converter` — conversão (FormData com `ficheiros`, opção `tipo` e `tamanho`)
- **Conversões:**
  - **HEIC → JPG** — usa `pillow_heif`, dropzone drag & drop, validações: extensão .heic, 10MB/ficheiro, máx 20
  - **PNG/JPG → ICO** — usa Pillow `resize` com `Image.LANCZOS`, tamanhos: 16, 32, 48, 64, 128, 256px
- **Funcionalidades:**
  - Seletor de tipo via tabs no frontend
  - 1 ficheiro → download direto; 2+ ficheiros → download ZIP
  - Lista de ficheiros selecionados com remoção individual
  - Histórico das últimas 10 conversões com data, contagem e tamanho
  - Zero disco — tudo processado em memória

### Área Admin (`app/admin/`)
- Blueprint em `/admin`, decorador `@admin_required`
- Ícone 🛠️ na navbar visível apenas para admins
- Dashboard com estatísticas, lista de utilizadores, toggle activo/admin, apagar utilizador
- **Gestão de Convites** — nova funcionalidade:
  - `GET /admin/convites` — lista todos os convites (activos, usados, expirados)
  - `POST /admin/convites/gerar` — gera convite único (token criptográfico) com email, 7 dias de validade; pode enviar por email (SendGrid) ou gerar link para copiar
  - `POST /admin/convites/<id>/revogar` — revoga convite não utilizado
- Template `admin/convites.html` com formulário AJAX e tabela de estado
- Reutiliza `EmailChannel` (SendGrid) para envio automático
- Protecção: não é possível afectar a própria conta

### Navegação
- **Navbar** — marca PIPE (link para dashboard) + utilizador / admin / definições / sair
- **Dashboard** — cards de módulos. Adicionar novos módulos aqui.
- Links de módulos removidos da navbar — não escala com muitos módulos

### Módulo Assistente IA (`app/assistente/`) — em desenvolvimento
- **Sem BD** — módulo stateless, histórico de conversa em Flask session
- **Ficheiros:**
  - `cliente.py` — chamada HTTP a OpenRouter API com retry (3 tentativas com backoff 2s/5s/10s) e fallback entre modelos
  - `contexto.py` — orquestração de tool use; histórico limitado a 20 mensagens (10 trocas); system prompt em PT-PT com regras explícitas de leitura apenas
  - `ferramentas.py` — tool use com 4 funções: `get_tarefas`, `get_notas`, `get_euromilhoes`, `get_resumo_geral`; todas filtram por `user_id` (obrigatório, injetado pelo caller)
  - `routes.py` — rotas: `GET /assistente`, `POST /assistente/api/chat` (30/min), `POST /assistente/api/limpar` (10/min)
- **Frontend:** balões de chat com cores distintas (utilizador = âmbar, assistente = azul-acinzentado), boas-vindas automáticas com delay de 800ms
- **Variáveis de ambiente:** `OPENROUTER_API_KEY` (obrigatória), `OPENROUTER_MODEL` (opcional, default `qwen/qwen3.6-plus:free`)

### Sistema de notificações (`app/notifications/`)
- Serviço central `NotificationService` — `notification_service.send(user, type, subject, body, data)`
- `TelegramChannel` ✅ e `EmailChannel` ✅ (SendGrid)
- `UserNotificationPreferences` na BD; página de definições em `/definicoes`

### Scheduled task — `scripts/pipe_tasks.py`
Script unificado que corre 1x/dia no PA (08:00). Cada módulo é uma função independente.

| Módulo | Quando actua | O que faz |
|---|---|---|
| `tarefa_euromilhoes` | Terças e sextas | Verifica resultados e notifica utilizadores com jogos |
| `tarefa_tarefas` | Todos os dias | Notifica tarefas em atraso (diariamente enquanto persistirem) |

**Notificações de atraso diárias:** campo `notificada_em` (Date). Se `notificada_em < hoje` ou `NULL`, notifica e actualiza para hoje. Ao editar o prazo, `notificada_em` é resetado para `NULL`.

### Autenticação 2FA
- Telegram ✅, Email ✅, TOTP ✅ (pyotp + qrcode)
- Múltiplos métodos em simultâneo — utilizador escolhe no login

### Design System (`app/static/css/pipe.css`)
- Tema escuro, acentos âmbar/dourado
- Componentes: navbar, cartões, formulários, botões, alertas, skeleton loader, toggles, modais
- Componentes Euromilhões: bolas, barras de frequência, badges de resultado
- Componentes Tarefas: sidebar de listas, items com barra de prioridade, check circular, campo de busca, badges, estado vazio; selector mobile de listas (CSS inline no template)
- Componentes Notas: grelha de cartões, cartão com hover/acções, palete de cores, caixa de criação inline, checklist, sidebar de etiquetas, página de edição
- Módulo Passwords reutiliza exclusivamente classes existentes do design system — sem CSS adicional
- Layout responsivo (sidebar oculta em mobile)

### Segurança

| Medida | Implementação | Ficheiro |
|---|---|---|
| CSRF | Flask-WTF CSRFProtect em todos os formulários | `app/__init__.py` |
| Rate limiting | Flask-Limiter nas rotas críticas — login (10/min), registo (5/h), recuperação (5/h), 2FA (10/min) | `app/auth/routes.py`, `app/extensions.py` |
| Logging de login falhado | `app.logger.warning` com username e IP do utilizador | `app/auth/routes.py` |
| Security headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` | `app/__init__.py` |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` | `app/auth/models.py` |
| Controlo de acesso | `@login_required` e `@admin_required` | rotas protegidas |
| Configuração IP PA | `X-Forwarded-For` no Limiter para proxy reverso do PythonAnywhere | `app/extensions.py` |

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
- **Sistema de Convites** ✅ — geração de link, envio por email (SendGrid), registo por token, validação de 7 dias, uso único
- Módulo Tarefas completo ✅
- `pipe_tasks.py` com módulo Tarefas ✅
- Módulo Tarefas — vista "Todas" por defeito ao abrir ✅
- Módulo Tarefas — selector mobile de listas ✅
- Módulo Notas — criação inline (texto e checklist) ✅
- Módulo Notas — cores de fundo ✅
- Módulo Notas — fixar / arquivar / recuperar ✅
- Módulo Notas — etiquetas ✅
- Módulo Notas — busca em tempo real ✅
- Módulo Notas — toggle checklist no cartão ✅
- Módulo Notas — edição completa ✅
- Módulo Notas — deployed no PythonAnywhere ✅
- Módulo Passwords — geração de password ✅
- Módulo Passwords — geração de passphrase ✅
- Módulo Passwords — geração de PIN ✅
- Módulo Passwords — barra de força ✅
- Módulo Passwords — botão copiar ✅
- Módulo Passwords — deployed no PythonAnywhere ✅
- Módulo Câmbio — conversão EUR → BRL ✅

---

## Deploy — PythonAnywhere

### Estado
- **App online** em `https://felipejn.pythonanywhere.com` ✅
- **WSGI configurado** ✅
- **Static files** configurados ✅
- **Scheduled task** — `python /home/felipejn/pipe-app/scripts/pipe_tasks.py` às 08:00 ✅

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
SENDGRID_API_KEY=...
SENDGRID_FROM_EMAIL=...
WISE_API_KEY=...
```

### Migrações de BD executadas
- `scripts/adicionar_is_admin.py` ✅
- `scripts/migrar_notificada_em.py` ✅
- Módulo Notas — tabelas criadas automaticamente por `db.create_all()` ✅
- Módulo Loja — tabela `user_modulos` criada por `db.create_all()` ✅
- Módulo Passwords — sem BD, sem migrações ✅

---

## Arquitectura de módulos

Cada módulo é um Flask Blueprint independente.
A navegação é feita pelos cards no dashboard.

**Para adicionar um novo módulo:**
1. Criar `app/<modulo>/` com `__init__.py` e `routes.py` (+ `models.py` se precisar de BD)
2. Registar o blueprint em `app/__init__.py`
3. Adicionar card em `app/templates/dashboard.html`
4. Adicionar função `tarefa_<modulo>(hoje)` em `scripts/pipe_tasks.py` se precisar de tarefa agendada

**Padrão AJAX/fetch no PIPE:**
- Passar sempre `'X-CSRFToken': '{{ csrf_token() }}'` no header do fetch
- Backend usa `request.get_json()` — não usa `validate_on_submit()`

---

## Ponto onde estamos

**Versão v1.1** — sete módulos completos e deployed. Infraestrutura madura: auth com 2FA multi-método, rate limiting, logging de segurança, security headers, sessões permanentes para PWA, notificações Telegram + Email, área admin, sistema de loja de módulos para personalização por utilizador, scheduled task unificada a correr às 08:00. Sistema de convites implementado e testado (registo restrito por link de 7 dias, uso único). Auditoria de segurança coberta: CSRF, brute force protection, clickjacking protection, MIME sniffing protection, login event logging.

**Pendências conhecidas:**
- **Assistente IA**: conexão com API falha frequentemente (necessário melhorar retry/fallback)
- **Melhorias em módulos existentes**: lista de tarefas (exportação?), notas (ordenar etiquetas manualmente?), etc. — por especificar
- **Chat interno**: plano documentado mas não implementado (adiado por decisão)

---

## Próximos passos

- **Assistente IA**: estabilizar conexão com API (melhorar retry/fallback, monitorizar rate limits)
- **Melhorias nos módulos existentes**: 
  - Tarefas: exportação de lista?
  - Notas: ordenação manual de etiquetas?
  - Dashboard:.activity feed?
- Revisitar **Chat Interno** apenas quando houver necessidade real de comunicação entre utilizadores
- Novos módulos com valor prático (arquitectura pronta) — versão 1.x

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
- Notificações: Telegram ✅ + SendGrid email ✅ — arquitectura modular, canais independentes
- Admin: área restrita com gestão de utilizadores, decorador `@admin_required`, script CLI de promoção
- Scheduled task: `pipe_tasks.py` — script unificado, um módulo por função, isolamento de erros
- Rate limiting: Flask-Limiter com `X-Forwarded-For` para PythonAnywhere — protege rotas críticas (login, registo, recuperação de password, 2FA) contra brute force
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` — via `@app.after_request` em `create_app()`
- Login event logging: tentativas falhadas registadas com username e IP via `app.logger.warning`
