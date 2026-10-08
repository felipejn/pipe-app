# PIPE — Contexto para Claude

## Quick Stats
- **Projecto:** Flask web app — plataforma modular pessoal
- **Owner:** Felipe (apelido "Pipe") — ortografia Portuguesa Europeia em TODO o código e mensagens
- **Repo:** https://github.com/felipejn/pipe-app
- **Deploy:** https://felipejn.pythonanywhere.com (PythonAnywhere, plano free)
- **Versão actual:** v1.6.0 (Flask-Migrate — baseline `3b14f5bd26a5`; produção stamped em 2026-10-06) — detalhe em `Estado_Atual.md`
- **Testes:** 220 (pytest — nunca tocam na BD real)

## Referência principal
**Ler `Estado_Atual.md`** (nome com maiúsculas nesta platforma — em Linux/PA o sistema de ficheiros é case-sensitive) para o panorama completo do projecto — estrutura, módulos, rotas, segurança, deploy. Este ficheiro é a fonte de verdade.

## Regras inegociáveis
- Usar **sempre** Português Europeu (PT-PT) em comentários, mensagens e documentação
- Cada módulo é um **Flask Blueprint** independente
- Navegação via **dashboard** — sem links de módulos na navbar
- **Padrão AJAX:** `'X-CSRFToken': '{{ csrf_token() }}'` no header do fetch; backend usa `request.get_json()`
- Frontend usa **vanilla JS inline nos templates** — sem ficheiros JS externos por módulo
- **Estado actual** em `Estado_Atual.md` — manter sempre actualizado após mudanças significativas
- **Esquema da BD:** evolui só com Flask-Migrate — alterar modelo → `flask db migrate` → rever → testar → backup → `flask db upgrade` → `flask db current`/`flask db check`; a baseline `3b14f5bd26a5` é **imutável** (a produção foi stamped em 2026-10-06, sem executar a baseline sobre os dados); `db.create_all()` só corre em testes — os scripts de migração manuais são históricos e não devem ser executados
- **Testes nunca tocam na BD real:** criar a app com `create_app('testing')` (SQLite em memória + sessões em pasta temporária). Atribuir `app.config[...]` **depois** de `create_app()` não tem efeito — o engine do SQLAlchemy fica fixado em `db.init_app()` e o Flask-Session em `Session(app)`. Foi esse anti-padrão que apagou `instance/pipe.db`; `tests/conftest.py` agora bloqueia `db.drop_all()` com BD de ficheiro

## Módulos existentes
| Blueprint | Rota | State |
|---|---|---|
| `auth` | `/auth/*` | Com BD (User, 2FA, TOTP, Convite) — registo por convite only |
| `euromilhoes` | `/euromilhoes/` | Com BD (Jogo) |
| `tarefas` | `/tarefas/` | Com BD (Lista, Tarefa, TagTarefa) |
| `notas` | `/notas/` | Com BD (Nota, ItemChecklist, EtiquetaNota) |
| `passwords` | `/passwords/` | Com BD (CofreConfig, CofrePassword) + gerador stateless |
| `conversoes` | `/conversoes/` | Com BD (Conversao) |
| `modulos` | `/modulos/loja` | Com BD (UserModulo) — Loja de Módulos |
| `cambio` | `/cambio/` | Stateless (Wise API + fallback) |
| `cores` | `/cores/` | Stateless |
| `notifications` | — | Com BD (UserNotificationPreferences) |
| `admin` | `/admin/` | Sem BD |
| `settings` | `/definicoes/` | Sem BD |
| `calendario` | `/calendario/` | Com BD (Evento) |
| `combustiveis` | `/combustiveis/` | Com BD (5 tabelas; `Posto` globais) |
| `assistente` | `/assistente/` | Funcional — 17 tools: 7 de leitura + 10 de escrita (modos leitura/escrita) |

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
Flask 3.0, SQLAlchemy, Flask-Login, Flask-WTF, Werkzeug, Flask-Limiter, Flask-Migrate, Pillow, pyotp, requests

## Scheduled tasks
`scripts/pipe_tasks.py` — corre 1x/dia às 07:00 no PythonAnywhere

## Assistente IA
Módulo de chat com IA via OpenRouter, com tool use para consultar dados reais dos módulos do PIPE. Card no dashboard com badge "IA" e destaque visual. **Nota:** fila de modelos gratuitos validada contra o catálogo do OpenRouter (v1.4.6) — se a API ficar instável, confirmar que os IDs da fila ainda existem em `https://openrouter.ai/api/v1/models`.

### Arquitectura
- **Cliente** (`cliente.py`): `chamar_llm(mensagens, ferramentas=None)` — HTTP POST para `openrouter.ai/api/v1/chat/completions`. Modelo default via `OPENROUTER_MODEL` env var (default: `inclusionai/ling-3.0-flash-sante:free`) — **5 modelos no total (1 principal + 4 fallbacks)**. Auth por `OPENROUTER_API_KEY`. Retry com backoff (3 tentativas: 2s, 5s, 10s) + fallback entre modelos. Fila de fallbacks: `poolside/laguna-s-2.1:free`, `liquid/lfm-2.5-2.6b:free`, `nvidia/nemotron-3-super-120b-a12b:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`.
- **Contexto** (`contexto.py`): `processar_mensagem_assistente(mensagem_utilizador, user_id, historico=None)` — orquestra o fluxo: monta prompt + histórico, chama LLM, executa tool calls se necessário, guarda resposta. Histórico em Flask session (limite 20 mensagens = 10 trocas). O resultado de cada ferramenta é cortado antes de ser enviado ao modelo: listas a `LIMITE_ITENS_LISTA_TOOL` (10) itens e JSON a `LIMITE_CHARS_TOOL_RESULT` (2000) chars, com **degradação progressiva** (`LIMITES_ITENS_DEGRADACAO` = 10 → 8 → 5 → 3 → 1) — se exceder o tecto encolhem-se as listas em vez de se descartar o resultado (o aviso genérico é só o último recurso). Ferramentas com listas grandes devem devolver poucos campos por registo.
- **Ferramentas** (`ferramentas.py`): tool use com 7 funções de leitura — `get_tarefas`, `get_notas`, `get_euromilhoes`, `get_resumo_geral`, `get_eventos`, `get_cambio`, `get_combustiveis` — e 10 de escrita. Todas filtram por `user_id` (obrigatório, injetado pelo caller — nunca vem do modelo). Nota: no módulo Combustíveis os `Posto` são globais e sem `user_id`, pelo que o isolamento de `get_combustiveis` é feito pelos concelhos de `UtilizadorConcelho` do utilizador. `get_combustiveis` aceita `tipo_combustivel`, `concelho`, `posto` (nome **ou** marca, insensível a acentos e maiúsculas — usar sempre que a pergunta nomeie um posto), `apenas_mais_barato` e `limite`.
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
- Dois modos: **leitura** (default — só consulta; encaminha o utilizador para o módulo para acções de escrita) e **escrita** (10 tools de escrita, activadas via toggle no chat e `POST /assistente/api/modo`; limite de 10 escritas/min)
- Nunca inventar dados — usar ferramentas quando precisa de dados concretos
- Responder directamente para perguntas simples (cumprimentos, explicações)
- Tom formal e profissional, respostas concisas

### Variáveis de ambiente
- `OPENROUTER_API_KEY` — chave da OpenRouter (obrigatória)
- `OPENROUTER_MODEL` — modelo a usar (default: `inclusionai/ling-3.0-flash-sante:free`)

### CSS (`pipe.css`)
- Classes `chat-bubble`, `chat-bubble--user`, `chat-bubble--assistant` para balões
- Classe `cartao-novo` + `badge-novo` para destaque no dashboard
