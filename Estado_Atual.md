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
│   │   ├── euromilhoes/
│   │   └── settings/
│   ├── auth/                # Blueprint auth
│   │   ├── __init__.py
│   │   ├── routes.py        # /auth/login, /auth/registo, /auth/logout
│   │   ├── forms.py         # LoginForm, RegistoForm
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
- Formulários com validação: `LoginForm`, `RegistoForm`
- Rotas: `/auth/login`, `/auth/registo`, `/auth/logout`
- Script utilitário `scripts/criar_admin.py` para criar o primeiro utilizador

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

### Sistema de notificações (`app/notifications/`)
- Serviço central `NotificationService` — cada módulo chama apenas `notification_service.send()`
- `TelegramChannel` — Bot API Telegram, testado e a funcionar ✅
- `EmailChannel` — SendGrid API v3, testado e a funcionar ✅
- `UserNotificationPreferences` — preferências por utilizador na BD (canal activo, chat_id, tipos)
- Página de definições em `/definicoes` com toggles por canal e botões de teste
- `scripts/verificar_resultados.py` — scheduled task para o PA (corre às 23:00 às terças e sextas)

### Design System (`app/static/css/pipe.css`)
- Tema escuro com acentos em âmbar/dourado
- Componentes base: navbar, cartões, formulários, botões, alertas, bolas de números/estrelas
- Componentes adicionais: filtro de período, skeleton loader, spinner, toggle de data, barras de frequência, badges de resultado, toggle switch, página de definições
- Layout responsivo (grid de 2 colunas colapsa para 1 em mobile)
- Templates: `base.html`, `dashboard.html`, `auth/login.html`, `auth/register.html`, `euromilhoes/index.html`, `euromilhoes/resultados.html`, `euromilhoes/frequencias.html`, `settings/index.html`

### Testes realizados localmente
- Login e registo de utilizador ✅
- Dashboard ✅
- Registo de jogo (data próximo sorteio e data manual) ✅
- Gerador aleatório ✅
- Apagar jogo ✅
- Página de resultados com skeleton loader ✅
- Página de frequências ✅
- Notificação Telegram (teste manual) ✅
- Notificação Email SendGrid (teste manual) ✅
- Script `verificar_resultados.py` (teste manual com dia comentado) ✅

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

O 2FA é obrigatório para todos os utilizadores.
O utilizador pode ter múltiplos métodos activos em simultâneo e escolhe qual usar no momento do login.

### Métodos planeados
| Método | Biblioteca | Descrição |
|---|---|---|
| TOTP | `pyotp` + `qrcode` | Google Authenticator / Authy — código gerado localmente |
| Telegram | canal existente | Bot envia código de 6 dígitos |
| Email | canal existente | SendGrid envia código de 6 dígitos |

### Fluxo de login com 2FA
1. Utilizador introduz username + password
2. Se credenciais válidas → redireciona para página de verificação 2FA
3. Utilizador escolhe o método e introduz o código
4. Código válido → acesso concedido

---

## Ponto onde estamos

O módulo Euromilhões está completo e testado. O sistema de notificações está implementado e testado (Telegram + Email). A scheduled task está pronta para configurar no PA. A arquitectura do 2FA está definida, implementação a iniciar.

---

## Próximos passos (por ordem)

### 1. Autenticação 2FA
- Obrigatório para todos os utilizadores
- Métodos: TOTP (`pyotp` + `qrcode`), Telegram, Email
- Utilizador pode ter múltiplos métodos activos — escolhe qual usar no login
- Adicionar ao modelo `User`: `totp_secret`, `dois_fa_activo`
- Novas rotas em `app/auth/`: `/auth/2fa/verificar`, `/auth/2fa/configurar`
- Interface na página de definições (`/definicoes`)

### 2. Deploy no PythonAnywhere
```bash
git clone https://github.com/felipejn/pipe-app.git
cd pipe-app
pip install -r requirements.txt --user
cp .env.example .env   # preencher todas as variáveis
python scripts/criar_admin.py
```
- Configurar `wsgi.py` com o username do PA
- Configurar scheduled task: `python ~/pipe-app/scripts/verificar_resultados.py` às 23:00

### 3. Novos módulos PIPE
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
```

## Variáveis de ambiente (`.env`)
```
FLASK_ENV=development
SECRET_KEY=...

# Telegram
TELEGRAM_BOT_TOKEN=...

# SendGrid
SENDGRID_API_KEY=...
SENDGRID_FROM_EMAIL=...
```

## Contexto técnico
- Python com ortografia Portuguesa Europeia em todos os comentários e mensagens
- Hosting alvo: PythonAnywhere (plano free) — espaço em disco não é problema (~37MB para .venv)
- Custo total: zero
- Base de dados: SQLite
- Autenticação actual: username/password — 2FA obrigatório a implementar
- Notificações: Telegram ✅ + SendGrid email ✅ — arquitectura modular, canais independentes
