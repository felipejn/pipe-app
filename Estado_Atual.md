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

## Ponto onde estamos

O módulo Euromilhões está funcionalmente completo com todas as funcionalidades dos scripts originais migradas para a interface web. A aplicação corre localmente e está actualizada no GitHub.

---

## Próximos passos sugeridos (por ordem)

### 1. Autenticação 2FA (TOTP)
Adicionar 2FA via app de autenticação (Google Authenticator / Authy).
Biblioteca sugerida: `pyotp` + `qrcode`.
Já previsto na arquitectura — não requer mudanças estruturais.

### 2. Notificações Telegram
Bot Telegram para notificações automáticas de resultados.
`api.telegram.org` está na lista de domínios permitidos no PythonAnywhere free.
Scheduled task no PA (1x por dia) — verificar às terças e sextas.

### 3. Deploy no PythonAnywhere
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

### 4. Novos módulos PIPE
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
- Notificações: Telegram (Gmail SMTP bloqueado no PA free; SendGrid como alternativa email)
