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
│   ├── models.py
│   ├── static/
│   │   └── css/pipe.css     # design system (tema escuro, âmbar/dourado)
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── auth/
│   │   └── euromilhoes/
│   ├── auth/                # Blueprint auth
│   │   ├── __init__.py
│   │   ├── routes.py        # /auth/login, /auth/registo, /auth/logout
│   │   └── forms.py         # LoginForm, RegistoForm
│   └── euromilhoes/         # Blueprint Euromilhões
│       ├── __init__.py
│       ├── routes.py
│       ├── models.py        # modelo Jogo (SQLite)
│       └── api.py           # consumo API pública + retry exponencial
├── scripts/
│   └── criar_admin.py
├── instance/
│   └── pipe.db              # SQLite (excluído do git)
├── .env                     # variáveis locais (excluído do git)
├── .env.example
├── requirements.txt
└── run.py
```
- App factory (`create_app`) com suporte a configurações Development/Production
- Flask-SQLAlchemy com SQLite (`instance/pipe.db`)
- Flask-Login para gestão de sessões
- Flask-WTF para formulários com protecção CSRF
- Dois Blueprints registados: `auth` e `euromilhoes`

### Estrutura alvo (com notificações)
```
pipe-app/
├── app/
│   ├── notifications/       # NOVO — serviço central de notificações
│   │   ├── __init__.py      # expõe notification_service
│   │   ├── service.py       # NotificationService
│   │   ├── models.py        # UserNotificationPreferences (BD)
│   │   └── channels/
│   │       ├── base.py      # classe abstracta BaseChannel
│   │       ├── telegram.py  # TelegramChannel
│   │       └── email.py     # EmailChannel (SendGrid)
│   ├── auth/
│   ├── euromilhoes/
│   └── [módulos futuros]/
└── ...
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

### Design System (`app/static/css/pipe.css`)
- Tema escuro com acentos em âmbar/dourado
- Componentes base: navbar, cartões, formulários, botões, alertas, bolas de números/estrelas
- Componentes adicionais: filtro de período, skeleton loader, spinner, toggle de data, barras de frequência, badges de resultado
- Layout responsivo (grid de 2 colunas colapsa para 1 em mobile)
- Templates: `base.html`, `dashboard.html`, `auth/login.html`, `auth/register.html`, `euromilhoes/index.html`, `euromilhoes/resultados.html`, `euromilhoes/frequencias.html`

### Testes realizados localmente
- Login e registo de utilizador ✅
- Dashboard ✅
- Registo de jogo (data próximo sorteio e data manual) ✅
- Gerador aleatório ✅
- Apagar jogo ✅
- Página de resultados com skeleton loader ✅
- Página de frequências ✅

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
| `TelegramChannel` | Planeado (prioritário) | `api.telegram.org` permitido no PA free |
| `EmailChannel` | Planeado | SendGrid — 100 emails/dia grátis, domínio permitido no PA |
| `WebPushChannel` | Futuro | Notificações browser |

**Nota:** Gmail SMTP bloqueado no PythonAnywhere free. WhatsApp descartado (sem solução gratuita sustentável).

---

## Ponto onde estamos

O módulo Euromilhões está funcionalmente completo com todas as funcionalidades dos scripts originais migradas para a interface web. A aplicação corre localmente e está actualizada no GitHub. A arquitectura de notificações está definida mas não implementada.

---

## Próximos passos (por ordem)

### 1. Implementar NotificationService + TelegramChannel
Criar `app/notifications/` conforme arquitectura definida acima.
Começar por `service.py` e `channels/telegram.py`.
Scheduled task no PA (1x por dia) — verificar resultados às terças e sextas.

### 2. Implementar EmailChannel (SendGrid)
`channels/email.py` com SendGrid como canal de email.

### 3. Autenticação 2FA (TOTP)
Adicionar 2FA via app de autenticação (Google Authenticator / Authy).
Biblioteca sugerida: `pyotp` + `qrcode`.
Já previsto na arquitectura — não requer mudanças estruturais.

### 4. Deploy no PythonAnywhere
```bash
# No PA:
git clone https://github.com/felipejn/pipe-app.git
cd pipe-app
pip install -r requirements.txt --user
cp .env.example .env   # preencher SECRET_KEY
python scripts/criar_admin.py
```
Configurar o ficheiro `wsgi.py` com o username do PA.

### 5. Novos módulos PIPE
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
```

## Contexto técnico
- Python com ortografia Portuguesa Europeia em todos os comentários e mensagens
- Hosting alvo: PythonAnywhere (plano free)
- Custo total: zero
- Base de dados: SQLite
- Autenticação actual: username/password — 2FA previsto para fase seguinte
- Notificações: Telegram (prioritário) + SendGrid (email) — arquitectura modular definida
