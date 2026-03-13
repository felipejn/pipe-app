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

### Estrutura do projecto (Flask)
- App factory (`create_app`) com suporte a configurações Development/Production
- Flask-SQLAlchemy com SQLite (`instance/pipe.db`)
- Flask-Login para gestão de sessões
- Flask-WTF para formulários com protecção CSRF
- Dois Blueprints registados: `auth` e `euromilhoes`

### Módulo Auth (`app/auth/`)
- Modelo `User` com password em hash (Werkzeug)
- Formulários com validação: `LoginForm`, `RegistoForm`
- Rotas: `/auth/login`, `/auth/registo`, `/auth/logout`
- Script utilitário `scripts/criar_admin.py` para criar o primeiro utilizador

### Módulo Euromilhões (`app/euromilhoes/`)
- Modelo `Jogo` (SQLite) — substitui o `jogos.json` dos scripts anteriores
- `api.py` — consome a API pública com retry exponencial (3 tentativas, backoff 5s/10s/20s)
- Rotas: listar jogos, registar jogo, apagar jogo, gerar combinação aleatória (endpoint JSON)
- Cálculo local do próximo sorteio (terça ou sexta)

### Design System (`app/static/css/pipe.css`)
- Tema escuro com acentos em âmbar/dourado
- Componentes: navbar, cartões, formulários, botões, alertas, bolas de números/estrelas
- Layout responsivo (grid de 2 colunas colapsa para 1 em mobile)
- Templates: `base.html`, `dashboard.html`, `auth/login.html`, `auth/register.html`, `euromilhoes/index.html`

---

## Ponto onde estamos

O scaffold está completo e no GitHub. A aplicação **ainda não foi testada a correr** — o próximo passo é arrancar localmente e verificar que tudo funciona.

---

## Próximos passos sugeridos (por ordem)

### 1. Primeiro arranque local (prioritário)
```bash
pip install -r requirements.txt
python scripts/criar_admin.py
python run.py
```
Verificar: login, registo, dashboard, módulo Euromilhões, registar jogo, apagar jogo, gerar combinação.

### 2. Integrar lógica dos scripts originais
Os scripts `euromilhoes.py`, `euromilhoes_frequencia.py` e `euromilhoes_gerador.py` já existem e funcionam.
Migrar a lógica de verificação de resultados e análise de frequências para as rotas Flask.

### 3. Página de resultados
Ver resultados dos jogos registados com filtro por período (último sorteio / 30 dias / 90 dias / todos).
Mostrar acertos e prémios ganhos — lógica já existe em `api.py` (`verificar_acertos`).

### 4. Página de frequências
Análise histórica de números e estrelas com visualização (barras, top 5 mais/menos frequentes).
Pode ser uma página dentro do módulo Euromilhões.

### 5. Autenticação 2FA (TOTP)
Adicionar 2FA via app de autenticação (Google Authenticator / Authy).
Biblioteca sugerida: `pyotp` + `qrcode`.
Já previsto na arquitectura — não requer mudanças estruturais.

### 6. Notificações Telegram
Bot Telegram para notificações automáticas de resultados.
`api.telegram.org` está na lista de domínios permitidos no PythonAnywhere free.
Scheduled task no PA (1x por dia) — verificar às terças e sextas.

### 7. Deploy no PythonAnywhere
Quando o projecto estiver estável localmente:
```bash
# No PA:
git clone https://github.com/felipejn/pipe-app.git
cd pipe-app
pip install -r requirements.txt --user
cp .env.example .env   # preencher SECRET_KEY
python scripts/criar_admin.py
```
Configurar o ficheiro `wsgi.py` com o username do PA.

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
- Notificações: Telegram (Gmail SMTP bloqueado no PA free; SendGrid como alternativa email)
