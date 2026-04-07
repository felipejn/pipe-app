# PIPE — Módulo Assistente IA: Briefing para continuação

## Contexto do projecto

**PIPE** (Plataforma Inteligente Pessoal e Expansível) é uma aplicação web Flask modular, deployed em `https://felipejn.pythonanywhere.com` (PythonAnywhere, plano free). Repositório: `https://github.com/felipejn/pipe-app`.

### Módulos existentes (v1.0 — todos deployed e funcionais)
- **Euromilhões** — tracking de jogos, resultados via API, frequências
- **Tarefas** — listas, prioridades, prazos, notificações de atraso
- **Notas** — cards estilo Google Keep, checklists, etiquetas, cores
- **Passwords** — gerador stateless (password, passphrase, PIN)
- **Câmbio** — conversão de moedas via Wise API
- **Conversões** — HEIC→JPG, PNG/JPG→ICO, processamento em memória
- **Cores Flutter** — conversor de cores para código Flutter

### Infraestrutura transversal
- Auth com 2FA (TOTP, Telegram, Email)
- Flask-Limiter com ProxyFix para PythonAnywhere
- Notificações via Telegram Bot API e SendGrid
- Scheduled task `pipe_tasks.py` às 08:00
- SQLite + SQLAlchemy ORM
- Design system: tema escuro, acentos âmbar (`#f59e0b`)
- Ortografia: **Português Europeu** em todo o código, comentários e UI

---

## Decisões estratégicas tomadas nesta sessão

### Sobre o frontend
- **Não vale a pena investir em melhorias de frontend Jinja2** — rendimento decrescente
- A separação API REST + SPA (Next.js/React) faz sentido, mas **no projecto da loja de bordados** (a construir de raiz), não no PIPE
- O PIPE cresce em **novos módulos úteis**, não em reescrita de frontend

### Sobre IA no PIPE
- **OpenRouter.ai está confirmado na whitelist do PythonAnywhere free** — acesso garantido sem pedir adição
- OpenRouter dá acesso a 400+ modelos (Claude, GPT, Gemini, Llama, DeepSeek) com **uma única API key** e endpoint compatível com OpenAI SDK
- Modelos gratuitos disponíveis: `meta-llama/llama-3.3-70b-instruct:free`, `deepseek/deepseek-r1:free`, `google/gemini-flash-1.5:free` (entre outros com sufixo `:free`)
- **Custo zero é garantido** usando modelos com sufixo `:free`

---

## Módulo a construir: Assistente PIPE

### Conceito
Chatbot com acesso a todos os módulos do PIPE. O utilizador conversa em linguagem natural e o assistente consulta os seus dados reais (tarefas, notas, Euromilhões, etc.) para responder.

### Interface
- Chat multi-turno (histórico de conversa)
- Histórico **não persistido em BD** — vive em `session['chat_historico']` (Flask session)
- Quando o browser fecha, o histórico reinicia — comportamento intencional, sem migrações necessárias

### Dados acessíveis
Todos os módulos: tarefas, notas, Euromilhões — filtrados **obrigatoriamente** por `user_id = current_user.id` ao nível do Python (nunca do prompt).

### Modelo padrão
`meta-llama/llama-3.3-70b-instruct:free` — melhor equilíbrio entre capacidade de tool use e disponibilidade no tier gratuito. Configurável via variável de ambiente `OPENROUTER_MODEL` para trocar sem tocar no código.

---

## Arquitectura definida

### Estrutura de ficheiros
```
app/assistente/
├── __init__.py
├── routes.py          # /assistente/ + POST /assistente/api/chat
├── ferramentas.py     # funções que consultam a BD por utilizador
└── contexto.py        # monta system prompt + executa tool calls

app/templates/assistente/
└── index.html         # interface de chat (tema escuro PIPE)
```

Registar blueprint em `app/__init__.py` + card no `dashboard.html`.

### Ferramentas disponíveis para o modelo
```python
get_tarefas(lista=None, estado=None, atrasadas=False)
get_notas(busca=None, etiqueta=None, arquivadas=False)
get_euromilhoes(ultimos_n=5)
get_resumo_geral()   # stats rápidas de todos os módulos
```

Estas funções reutilizam as queries SQLAlchemy já existentes nos módulos, embrulhadas com filtro `user_id`.

### Abordagem de contexto: Tool Use (Function Calling)
O modelo decide o que precisa de consultar e chama as ferramentas — não recebe um dump de todos os dados de uma vez. Mais escalável, mais correcto, mais impressionante para portfolio.

**Fluxo de uma mensagem:**
```
1. Utilizador envia mensagem via AJAX
2. routes.py recebe, chama contexto.py
3. contexto.py monta: system prompt + histórico de sessão + mensagem nova
4. POST https://openrouter.ai/api/v1/chat/completions (com definição das ferramentas)
5. Modelo responde com tool_call (ex: get_tarefas(atrasadas=True))
6. ferramentas.py executa a query filtrada por user_id
7. Resultado devolvido ao modelo numa segunda chamada
8. Modelo formula resposta em linguagem natural
9. AJAX actualiza o chat no browser
```

Duas chamadas à API por mensagem com tool use — dentro dos rate limits gratuitos.

### Integração com OpenRouter
```python
# app/assistente/cliente.py
import requests, os

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELO_PADRAO = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

def chamar_llm(mensagens, ferramentas=None):
    payload = {
        "model": MODELO_PADRAO,
        "messages": mensagens,
    }
    if ferramentas:
        payload["tools"] = ferramentas
    
    resposta = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=30
    )
    resposta.raise_for_status()
    return resposta.json()
```

### Variável de ambiente a adicionar ao `.env`
```
OPENROUTER_API_KEY=<chave gerada em openrouter.ai>
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

---

## Padrões do PIPE a respeitar

- **CSRF**: `X-CSRFToken` no header de todos os fetch AJAX
- **CSS**: reutilizar classes existentes do `pipe.css` — sem CSS adicional se possível
- **Formulários**: `campo-texto` para inputs de texto
- **JSON responses**: incluir campos actualizados após commit
- **Blueprints**: registar em `app/__init__.py`, card em `dashboard.html`
- **Sem Flask-Migrate**: migrações manuais via scripts em `scripts/`; `db.create_all()` para tabelas novas (este módulo não precisa de BD)
- **Rate limiting**: aplicar `@limiter.limit(...)` na rota POST do chat

---

## Questões por resolver antes de implementar

1. **Fallback quando não há tool use**: se o modelo não chamar ferramentas e responder directamente (o que acontece com queries simples como "olá"), o fluxo tem de lidar com isso graciosamente.

2. **Rate limits dos modelos gratuitos**: os modelos `:free` no OpenRouter têm limites (tipicamente 20 req/min, 200 req/dia por modelo). Decidir se mostramos um erro claro ao utilizador ou fazemos fallback automático para outro modelo gratuito.

3. **Tamanho do histórico de sessão**: definir quantas mensagens de histórico se passam ao modelo (sugestão: últimas 10 trocas = 20 mensagens) para não exceder o contexto.

4. **System prompt**: redigir o prompt inicial que define o comportamento do assistente — tom, língua (PT-PT), capacidades declaradas, e instrução de nunca inventar dados.

5. **Segurança**: confirmar que cada função em `ferramentas.py` filtra por `current_user.id` — isto é inegociável e deve ser revisto em code review.

---

## Próximos passos concretos (ordem sugerida)

1. Criar conta no OpenRouter, gerar API key, testar acesso ao modelo via curl/script local
2. Adicionar `OPENROUTER_API_KEY` e `OPENROUTER_MODEL` ao `.env` local e ao PA
3. Implementar `app/assistente/ferramentas.py` com as 4 funções + filtro por user
4. Implementar `app/assistente/contexto.py` — lógica de tool use + gestão de histórico
5. Implementar `app/assistente/routes.py` — rota GET (página) + POST (API chat)
6. Criar `app/templates/assistente/index.html` — interface de chat no tema escuro PIPE
7. Registar blueprint + card no dashboard
8. Testar localmente com queries reais ("que tarefas tenho em atraso?", "resume as minhas notas desta semana")
9. Deploy: git push → git pull no PA → reload
10. Actualizar `Estado_Atual.md`

---

## Ficheiros do PIPE que o próximo chat deve conhecer

Para implementação, é útil partilhar (por zip ou conteúdo directo):
- `app/__init__.py` — para registar o blueprint correctamente
- `app/tarefas/models.py` — modelos Lista, Tarefa
- `app/notas/models.py` — modelos Nota, ItemChecklist, EtiquetaNota
- `app/euromilhoes/models.py` — modelo Jogo
- `app/templates/dashboard.html` — para adicionar o card
- `app/static/css/pipe.css` — para respeitar o design system
- `Estado_Atual.md` — estado completo do projecto (partilhar no início de cada sessão)
