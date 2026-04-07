# PIPE — Contexto para Claude

## Quick Stats
- **Projecto:** Flask web app — plataforma modular pessoal
- **Owner:** Felipe (apelido "Pipe") — ortografia Portuguesa Europeia em TODO o código e mensagens
- **Repo:** https://github.com/felipejn/pipe-app
- **Deploy:** https://felipejn.pythonanywhere.com (PythonAnywhere, plano free)
- **Versão actual:** v1.0

## Referência principal
**Ler `estado_atual.md`** para o panorama completo do projecto — estrutura, módulos, rotas, segurança, deploy. Este ficheiro é a fonte de verdade.

## Regras inegociáveis
- Usar **sempre** Português Europeu (PT-PT) em comentários, mensagens e documentação
- Cada módulo é um **Flask Blueprint** independente
- Navegação via **dashboard** — sem links de módulos na navbar
- **Padrão AJAX:** `'X-CSRFToken': '{{ csrf_token() }}'` no header do fetch; backend usa `request.get_json()`
- Frontend usa **vanilla JS inline nos templates** — sem ficheiros JS externos por módulo
- **Estado actual** em `estado_atual.md` — manter sempre actualizado após mudanças significativas

## Módulos existentes
| Blueprint | Rota | State |
|---|---|---|
| `auth` | `/auth/*` | Com BD (User, 2FA, TOTP) |
| `euromilhoes` | `/euromilhoes/` | Com BD (Jogo) |
| `tarefas` | `/tarefas/` | Com BD (Lista, Tarefa, TagTarefa) |
| `notas` | `/notas/` | Com BD (Nota, ItemChecklist, EtiquetaNota) |
| `passwords` | `/passwords/` | Stateless |
| `conversoes` | `/conversoes/` | Com BD (Conversao) |
| `cambio` | `/cambio/` | Stateless (Wise API + fallback) |
| `cores` | `/cores/` | Stateless |
| `notifications` | — | Com BD (UserNotificationPreferences) |
| `admin` | `/admin/` | Sem BD |
| `settings` | `/definicoes/` | Sem BD |
| `assistente` | `/assistente/` | Em desenvolvimento (WIP) |

## Para adicionar módulo
1. Criar `app/<modulo>/` com `__init__.py` + `routes.py` (+ `models.py` se BD)
2. Registar blueprint em `app/__init__.py`
3. Adicionar card em `app/templates/dashboard.html`
4. Se precisa de scheduled task: adicionar em `scripts/pipe_tasks.py`

## Segurança
- CSRF: Flask-WTF CSRFProtect global
- Rate limiting: Flask-Limiter nas rotas críticas
- 2FA: Telegram, Email, TOTP (múltiplos métodos simultâneos)
- Security headers em `app/__init__.py` via `@app.after_request`
- Login failures logged com `app.logger.warning`

## Tech stack
Flask 3.0, SQLAlchemy, Flask-Login, Flask-WTF, Werkzeug, Flask-Limiter, Pillow, pyotp, requests

## Scheduled tasks
`scripts/pipe_tasks.py` — corre 1x/dia às 08:00 no PythonAnywhere

## Assistente IA (WIP)
Módulo de chat com IA via OpenRouter, com tool use para consultar dados reais dos módulos do PIPE. Card no dashboard com badge "IA" e destaque visual.

### Arquitectura
- **Cliente** (`cliente.py`): `chamar_llm(mensagens, ferramentas=None)` — HTTP POST para `openrouter.ai/api/v1/chat/completions`. Modelo default via `OPENROUTER_MODEL` env var (default: `qwen/qwen3.6-plus:free`). Auth por `OPENROUTER_API_KEY`. Retry com backoff (3 tentativas: 2s, 5s, 10s) + fallback entre modelos.
- **Contexto** (`contexto.py`): `processar_mensagem_assistente(mensagem_utilizador, user_id, historico=None)` — orquestra o fluxo: monta prompt + histórico, chama LLM, executa tool calls se necessário, guarda resposta. Histórico em Flask session (limite 20 mensagens = 10 trocas).
- **Ferramentas** (`ferramentas.py`): tool use com 4 funções — `get_tarefas`, `get_notas`, `get_euromilhoes`, `get_resumo_geral`. Apenas leitura — não criam, editam nem apagam nada. Todas filtram por `user_id` (obrigatório, injetado pelo caller — nunca vem do modelo).
- **Rotas** (`routes.py`):
  - `GET /assistente` — página de chat com balões coloridos e boas-vindas automáticas (template `assistente/index.html`)
  - `POST /assistente/api/chat` — AJAX `{mensagem: "..."}` → `{resposta: "..."}` (rate limit: 30/min)
  - `POST /assistente/api/limpar` — limpa histórico da sessão (rate limit: 10/min)

### Frontend (`app/templates/assistente/index.html`)
- Balões de chat: utilizador = fundo âmbar (`--cor-primaria`), assistente = `#2a2f47`
- Mensagem de boas-vindas automática com 800ms delay (JS, sem custo de tokens)
- Auto-resize do textarea, Enter envia / Shift+Enter nova linha

### System prompt
- Respostas em PT-PT
- CAPACIDADES LIMITADAS A LEITURA — não sugerir acções que não pode executar (criar, editar, apagar). Enviar utilizador ao módulo respectivo.
- Nunca inventar dados — usar ferramentas quando precisa de dados concretos
- Responder directamente para perguntas simples (cumprimentos, explicações)
- Tom formal e profissional, respostas concisas

### Variáveis de ambiente
- `OPENROUTER_API_KEY` — chave da OpenRouter (obrigatória)
- `OPENROUTER_MODEL` — modelo a usar (default: `qwen/qwen3.6-plus:free`)

### CSS (`pipe.css`)
- Classes `chat-bubble`, `chat-bubble--user`, `chat-bubble--assistant` para balões
- Classe `cartao-novo` + `badge-novo` para destaque no dashboard
