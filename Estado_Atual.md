# PIPE — Estado Actual do Projecto

## O que é o PIPE
Plataforma Inteligente Pessoal e Expansível — aplicação web Flask modular.
O nome é simultaneamente um acrónimo e o apelido do utilizador (Felipe = Pipe).
O módulo Euromilhões é o primeiro módulo. A arquitectura suporta adição de novos módulos com a mesma identidade visual.

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
│   ├── static/
│   │   └── css/pipe.css     # design system (tema escuro, âmbar/dourado)
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── auth/
│   │   └── euromilhoes/
│   │   └── settings/
│   ├── auth/                # Blueprint auth
│   │   ├── __init__.py
│   │   ├── routes.py        # /auth/login, /auth/registo, /auth/logout, /auth/perfil, /auth/2fa/*
│   │   ├── forms.py         # LoginForm, RegistoForm, AlterarPasswordForm, VerificarCodigoForm, ConfigurarDoisFAForm, ConfirmarTOTPForm
│   │   └── models.py        # modelo User
│   ├── euromilhoes/         # Blueprint Euromilhões
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── models.py        # modelo Jogo (SQLite)
│   │   └── api.py           # consumo API pública + retry exponencial
│   ├── notifications/       # serviço central de notificações
│   │   ├── __init__.py      # expõe notification_service
│   │   ├── service.py       # NotificationService
│   │   ├── models.py        # UserNotificationPreferences (BD)
│   │   └── channels/
│   │       ├── base.py      # classe abstracta BaseChannel
│   │       ├── telegram.py  # TelegramChannel
│   │       └── email.py     # EmailChannel (SendGrid)
│   └── settings/            # Blueprint de definições
│       ├── __init__.py
│       └── routes.py        # /definicoes/
├── scripts/
│   ├── criar_admin.py
│   └── verificar_resultados.py  # scheduled task PA
├── instance/
│   └── pipe.db              # SQLite (excluído do git)
├── .env                     # variáveis locais (excluído do git)
├── .env.example
├── requirements.txt
└── run.py
```

### Módulo Auth (`app/auth/`)
- Modelo `User` com password em hash (Werkzeug)
- Formulários com validação: `LoginForm`, `RegistoForm`, `AlterarPasswordForm`, `VerificarCodigoForm`, `ConfigurarDoisFAForm`, `ConfirmarTOTPForm`, `PedirResetForm`, `ResetPasswordForm`
- Rotas: `/auth/login`, `/auth/registo`, `/auth/logout`, `/auth/perfil`
- Rotas 2FA: `/auth/2fa/verificar`, `/auth/2fa/escolher`, `/auth/2fa/enviar/<metodo>`, `/auth/2fa/reenviar`
- Rotas TOTP: `/auth/2fa/totp/configurar`, `/auth/2fa/totp/desactivar`
- Rotas recuperação de password: `/auth/recuperar-password`, `/auth/reset-password/<token>`
- Primeiro utilizador criado via `/auth/registo` na app (sem script necessário)

### Módulo Euromilhões (`app/euromilhoes/`)
- Modelo `Jogo` (SQLite) — substitui o `jogos.json` dos scripts anteriores
- `api.py` — consome a API pública com retry exponencial (3 tentativas, backoff 5s/10s/20s)
- Rotas implementadas:
  - `GET /` — listar jogos registados
  - `POST /registar` — registar novo jogo
  - `POST /apagar/<id>` — apagar jogo
  - `GET /gerar` — endpoint JSON para combinação aleatória
  - `GET /resultados` — página de resultados (carrega imediatamente)
  - `GET /resultados/dados` — endpoint JSON assíncrono com acertos da API
  - `GET /frequencias` — análise histórica de frequências
- Cálculo local do próximo sorteio (terça ou sexta)

### Funcionalidades implementadas
- **Registo de utilizador** — página `/auth/registo` com validação de duplicados (username e email)
- **Página de perfil** — `/auth/perfil` com dados da conta, alteração de password e configuração 2FA
- **Nome de utilizador na navbar** clicável → perfil
- **Registo de jogo** com selector de data: próximo sorteio (default) ou data manual
  - Validação JS: só aceita terças-feiras e sextas-feiras
  - Botão de registo bloqueado até data + 5 números + 2 estrelas seleccionados
- **Gerador aleatório** integrado no formulário de registo
- **Página de resultados** com carregamento em duas fases:
  - Fase 1 (imediata): jogos locais visíveis com skeleton loader animado
  - Fase 2 (assíncrona): fetch ao endpoint `/resultados/dados` preenche acertos, bolas do sorteio, badges e total ganho
  - Filtro por período: último sorteio / 30 dias / 90 dias / todos
  - Destaque visual em bolas com acerto (outline verde)
  - Tratamento de erro de API sem bloquear a página
- **Página de frequências** com análise histórica completa:
  - Top 5 números mais e menos frequentes
  - Top 3 estrelas mais e menos frequentes
  - Tabela completa 1–50 e 1–12 com barras proporcionais
  - Aviso explícito de que a frequência não prevê sorteios futuros
- **Recuperação de password** — fluxo completo por email:
  - Link "Esqueci a palavra-passe" na página de login
  - Token seguro gerado com `secrets.token_urlsafe(32)`, válido 1 hora
  - Email enviado via SendGrid com link de reset
  - Token consumido após uso (one-time) e apagado da BD
  - Resposta ao formulário sempre igual (evita enumeração de emails)

### Sistema de notificações (`app/notifications/`)
- Serviço central `NotificationService` — cada módulo chama apenas `notification_service.send()`
- `TelegramChannel` — Bot API Telegram, testado e a funcionar ✅
- `EmailChannel` — SendGrid API v3, testado e a funcionar ✅
- `UserNotificationPreferences` — preferências por utilizador na BD (canal activo, chat_id, tipos)
- Página de definições em `/definicoes` com toggles por canal e botões de teste
- `scripts/verificar_resultados.py` — scheduled task configurada no PA (corre às 23:00)

### Autenticação 2FA (`app/auth/`)
- **2FA opcional** — activado/desactivado na página de perfil por cada utilizador
- **Telegram** ✅ — código de 6 dígitos enviado via bot, expira em 10 minutos
- **Email** ✅ — código de 6 dígitos enviado via SendGrid, expira em 10 minutos
- **TOTP** ✅ — código gerado por Google Authenticator, MS Authenticator, Authy, etc.
- **Múltiplos métodos em simultâneo** — se vários activos, utilizador escolhe qual usar no login
- Fluxo: login com password → (se 2FA activo) escolha de método → código → acesso
- Campos no modelo `User`: `dois_fa_activo`, `dois_fa_chat_id`, `dois_fa_email_activo`, `dois_fa_codigo`, `dois_fa_expira`, `totp_secret`, `totp_activo`, `reset_token`, `reset_token_expira`
- Templates: `verificar_2fa.html`, `escolher_2fa.html`, `configurar_totp.html`

### Design System (`app/static/css/pipe.css`)
- Tema escuro com acentos em âmbar/dourado
- Componentes base: navbar, cartões, formulários, botões, alertas, bolas de números/estrelas
- Componentes adicionais: filtro de período, skeleton loader, spinner, toggle de data, barras de frequência, badges de resultado, toggle switch, página de definições, página de perfil, grelha 2 colunas, campos de informação (só leitura)
- Layout responsivo (grid de 2 colunas colapsa para 1 em mobile)
- Templates: `base.html`, `dashboard.html`, `auth/login.html`, `auth/registo.html`, `auth/perfil.html`, `auth/verificar_2fa.html`, `auth/escolher_2fa.html`, `auth/configurar_totp.html`, `auth/recuperar_password.html`, `auth/reset_password.html`, `euromilhoes/index.html`, `euromilhoes/resultados.html`, `euromilhoes/frequencias.html`, `settings/index.html`

### Testes realizados
- Login e registo de utilizador ✅
- Dashboard ✅
- Registo de jogo (data próximo sorteio e data manual) ✅
- Gerador aleatório ✅
- Apagar jogo ✅
- Página de resultados com skeleton loader ✅
- Página de frequências ✅
- Página de perfil (dados da conta + alterar password) ✅
- 2FA Telegram (activar, login com código, desactivar) ✅
- 2FA Email (activar, login com código, desactivar) ✅
- 2FA TOTP (activar com QR code, login com código, desactivar) ✅
- Escolha de método quando múltiplos activos ✅
- Notificação Telegram (teste manual) ✅
- Notificação Email SendGrid (teste manual) ✅
- Script `verificar_resultados.py` (teste manual com dia comentado) ✅
- App online no PythonAnywhere ✅
- Recuperação de password por email (pedido, email recebido, reset, login) ✅

---

## Deploy — PythonAnywhere

### Estado
- **App online** em `https://felipejn.pythonanywhere.com` ✅
- **WSGI configurado** — `/var/www/felipejn_pythonanywhere_com_wsgi.py` ✅
- **Static files** configurados — `/static/` → `/home/felipejn/pipe-app/app/static` ✅
- **Scheduled task** configurada — `python /home/felipejn/pipe-app/scripts/verificar_resultados.py` às 23:00 ✅
- **API externa** — `euromillions.api.pedromealha.dev` na whitelist do PA, consulta de resultados a funcionar ✅

### Configuração WSGI
```python
import sys
import os
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
```

### Notas de deploy
- Dependências instaladas com `pip install -r requirements.txt --user`
- Pasta `instance/` criada manualmente antes do primeiro arranque (`mkdir -p ~/pipe-app/instance`)
- Primeiro utilizador criado via `/auth/registo` na própria app (não é necessário script)
- Plano free PA: 512 MB disco, 100s CPU/dia — suficiente para uso pessoal

---

## Arquitectura de notificações (decisão de design)

O PIPE tem um serviço central de notificações transversal a todos os módulos.
Cada módulo chama apenas `notification_service.send()` sem conhecer os canais de entrega.
O serviço consulta as preferências do utilizador e despacha para os canais activos.

### Uso em qualquer módulo
```python
from app.notifications import notification_service

notification_service.send(
    user=current_user,
    type="resultado_euromilhoes",
    subject="Resultados de hoje",
    body="Verificámos os teus jogos...",
    data={"acertos": 3}
)
```

### Canais
| Canal | Estado | Notas |
|---|---|---|
| `TelegramChannel` | Implementado ✅ | Bot criado, token configurado no `.env` |
| `EmailChannel` | Implementado ✅ | SendGrid, remetente verificado, API key no `.env` |
| `WebPushChannel` | Futuro | Notificações browser |

---

## Arquitectura de 2FA (decisão de design)

O 2FA é opcional para cada utilizador e configurado na página de perfil.
O utilizador pode ter múltiplos métodos activos em simultâneo e escolhe qual usar no momento do login.

### Métodos implementados
| Método | Estado | Descrição |
|---|---|---|
| Telegram | Implementado ✅ | Bot envia código de 6 dígitos, expira em 10 min |
| Email | Implementado ✅ | SendGrid envia código de 6 dígitos, expira em 10 min |
| TOTP | Implementado ✅ | Google/MS Authenticator, Authy — `pyotp` + `qrcode` |

### Fluxo de login com 2FA
1. Utilizador introduz username + password
2. Se 0 métodos activos → acesso directo
3. Se 1 método activo → código enviado/solicitado automaticamente
4. Se 2+ métodos activos → página de escolha de método
5. Utilizador introduz o código → acesso concedido

### Fluxo de configuração TOTP
1. Perfil → "Configurar autenticador"
2. Secret gerado → QR code mostrado + chave manual para backup
3. Utilizador digitaliza com o autenticador
4. Introduz código de 6 dígitos para confirmar
5. TOTP activado — aparece como opção no login

---

## Ponto onde estamos

O PIPE está deployed e operacional em `https://felipejn.pythonanywhere.com`. O módulo Euromilhões está completo (jogos, gerador, frequências, resultados com consulta à API externa). O sistema de notificações está implementado (Telegram + Email). A autenticação está completa com 2FA via Telegram, Email e TOTP, e recuperação de password por email. A scheduled task está configurada no PA. Não há pendências de infraestrutura — o próximo foco é o desenvolvimento de novos módulos.

---

## Próximos passos (por ordem)

### 1. Novos módulos PIPE
A arquitectura com Flask Blueprints permite adicionar módulos independentes com a mesma identidade visual.

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
```

## Contexto técnico
- Python com ortografia Portuguesa Europeia em todos os comentários e mensagens
- Hosting: PythonAnywhere (plano free) — `https://felipejn.pythonanywhere.com`
- Custo total: zero
- Base de dados: SQLite
- Autenticação: username/password + 2FA opcional (Telegram ✅, Email ✅, TOTP ✅) + recuperação de password por email ✅
- Notificações: Telegram ✅ + SendGrid email ✅ — arquitectura modular, canais independentes
