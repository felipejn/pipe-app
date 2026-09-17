# Relatório de Entrega — Assistente PIPE: 4 ferramentas de leitura + 10 de escrita + modo de sessão

## Ficheiros alterados (só estes 4)

| Ficheiro | Alterações |
|---|---|
| `app/assistente/ferramentas.py` | +536 linhas: imports (`time`, `datetime`, `session`, `db`, `TagTarefa`, `ItemChecklist`, `Evento`, geradores de password), `CORES_EVENTO` (11 cores), `FERRAMENTAS_ESCRITA` (10), `LIMITE_ESCRITAS_POR_MINUTO=10`, `_limite_escrita_excedido()`, `_obter_ou_criar_lista/tags/etiquetas_nota()`, **10 ferramentas de escrita**, `DEFINICOES_FERRAMENTAS_LEITURA` (renomeado) + `_ESCRITA_EXTRA` + `_ESCRITA`, registo com 14 entradas, `executar_ferramenta(..., modo='leitura')` com portão de modo + débito + `try/except/rollback` |
| `app/assistente/contexto.py` | `MAX_TOOL_ITERATIONS=4`, `_contexto_temporal()` (+ `_DIAS_SEMANA`) anexado ao prompt a cada pedido, `SYSTEM_PROMPT_LEITURA` (texto actual preservado) + `SYSTEM_PROMPT_ESCRITA`, `processar_mensagem_assistente(..., modo=None)` reescrita como **ciclo `for`** com `for...else`, `_finalizar_erro()`, sleep de 2s por iteração |
| `app/assistente/routes.py` | Nova rota `POST /assistente/api/modo` (10/min); `index()` passa `modo` ao template; `session` importada ao topo |
| `app/templates/assistente/index.html` | Pílula indicadora + `label.toggle` (componente `.toggle` do design system), JS com fetch + CSRF, destaque âmbar em modo escrita, mensagens de sistema, boas-vindas ciente do modo |

**Bug corrigido:** `contexto.py` chamava `chamar_llm(mensagens)` na 2.ª chamada **sem `ferramentas=`** (L144 antigo) e sem limite de iterações. Agora passa `ferramentas=ferramentas` em todas as iterações e para ao fim de `MAX_TOOL_ITERATIONS=4`.

## Verificação executada (scripts temporários, já removidos)

- **Estrutura:** 4 leitura + 10 escrita = 14; registo 14; `FERRAMENTAS_ESCRITA`={10}; 11 cores; assinaturas correctas → **TUDO OK**
- **Integração** (BD SQLite temporária, 2 utilizadores, 12 secções): portão de modo, criar/alternar/apagar tarefas, confirmação obrigatória, criar notas (texto+checklist), fixar/arquivar/item, eventos, `notificada_em`, isolamento por `user_id`, limite 10/min (10 passam, 11.ª bloqueada), ferramenta desconhecida → **TODOS OS TESTES PASSARAM**
- **HTTP** (Flask test client): `GET /assistente` 200 + toggle renderizado; `POST /api/modo` grava na sessão; estado persiste entre pedidos; modo inválido → 400 → **TESTES HTTP PASSARAM**
- Nenhuma rota/modelo de `tarefas`, `notas` ou `calendario` foi tocada; `git status` mostra apenas os 4 ficheiros.

---

# Alteração adicional (pós-entrega) — Contexto temporal no system prompt

## Problema encontrado

Ao ser questionado sobre se o assistente consegue criar eventos, verificou-se que **nenhum dos dois `SYSTEM_PROMPT` injectava a data/hora actuais**. Como as ferramentas de escrita (`criar_evento`, `criar_tarefa`, `atualizar_evento`) exigem datas em **ISO 8601 absoluto**, o modelo não tinha forma de resolver expressões relativas ("amanhã", "na próxima sexta-feira") — arriscando datas inventadas.

## Solução aplicada (`app/assistente/contexto.py`)

- `from datetime import datetime` acrescentado aos imports.
- Nova tupla `_DIAS_SEMANA` com os 7 dias em português europeu. **Não** se usa `strftime('%A')` porque depende da locale do sistema e devolveria inglês por omissão.
- Nova função `_contexto_temporal()`, que devolve o bloco `DATA E HORA ACTUAIS` com dia da semana, data em `dd/mm/aaaa`, formato ISO e hora.
- O bloco é **calculado a cada pedido** (e não uma vez no import do módulo), para não ficar desactualizado quando a aplicação fica dias em execução — uma constante ao nível do módulo ficaria errada depois da meia-noite.
- `system_prompt += _contexto_temporal()` dentro de `processar_mensagem_assistente`, aplicado **aos dois modos** (leitura e escrita).

Exemplo do bloco gerado (execução de 16/09/2026):

```
DATA E HORA ACTUAIS
- Hoje é quarta-feira, 16/09/2026 (formato ISO: 2026-09-16).
- Hora actual: 17:07.
- Usa esta referência para converter expressões relativas em datas ISO 8601 absolutas antes de chamares as ferramentas.
```

## Verificação (script temporário, já removido — 18/18 passaram)

- Bloco contém cabeçalho, data ISO, data pt-PT, hora e **dia da semana correcto** (`quarta-feira` para 16/09/2026, confirmado por cálculo independente).
- `_DIAS_SEMANA` tem 7 entradas, índice 0 = `segunda-feira`, índice 6 = `domingo`.
- **Modo leitura:** prompt recebe o contexto temporal, mantém o texto original ("APENAS de leitura") e **não** expõe ferramentas de escrita.
- **Modo escrita:** prompt recebe o contexto temporal, mantém o texto original ("EXECUTAR ACÇÕES") e expõe `criar_evento`.
- Ordem das mensagens preservada: `system` primeiro, depois o histórico.
- `py_compile` OK nos 3 ficheiros Python.

> **Nota:** este bloco é informativo para o modelo; não altera validações. As ferramentas continuam a rejeitar datas em formato inválido ou com fim anterior ao início.

---

# ⚠️ Discrepâncias identificadas (para o teu registo / verificação)

Conforme pedido, executei o plano e decidi os casos ambíguos com base nas **rotas reais** (que o spec mandava confirmar). Aqui fica o registo do que **deve ser verificado/corrigido**:

### 1. `alternar_tarefa` — `notificada_em` (CORRIGIDO por mim)

- **Rota real** (`tarefas/routes.py` L297-298): ao concluir, faz `tarefa.notificada_em = None`.
- **Spec**: omitia isto.
- **Decisão:** adicionei `if tarefa.concluida: tarefa.notificada_em = None`, para paridade com a rota (evita re-notificar uma tarefa já concluída).
- `data_conclusao = utcnow() if concluida else None` — **confirmado igual à rota** ✅

### 2. `alternar_nota_acao` — `fixada` e `data_edicao` (CORRIGIDO por mim)

- **Rota real** (`notas/routes.py` L155-157): ao `arquivar`, faz também `nota.fixada = False`.
- **Rota real** (L169): actualiza **sempre** `nota.data_edicao = utcnow()`, em qualquer acção.
- **Spec**: omitia ambos.
- **Decisão:** adicionei `nota.fixada = False` no `toggle_arquivada` e `nota.data_edicao = utcnow()` antes do commit.

### 3. Nomes de acção diferentes dos da rota (NÃO alterado — decisão de design)

- A rota usa `'fixar'`, `'arquivar'`, `'toggle_item'`; o spec propõe `'toggle_fixada'`, `'toggle_arquivada'`, `'toggle_item'`.
- Como `alternar_nota_acao` é **interna ao assistente** (não é a rota HTTP), mantive os nomes do spec. **A confirmar:** se preferires uniformidade com a rota, há que renomear também o `enum` na definição da ferramenta.

### 4. `_obter_ou_criar_tags` — minúsculas (CORRIGIDO por mim)

- **Rota real** (L25): `[t.strip().lower() for t in ...]` — normaliza para minúsculas (e `TagTarefa` tem `UniqueConstraint('nome','user_id')`).
- **Spec**: preservava a capitalização → risco de `"Work"` e `"work"` coexistirem como tags distintas.
- **Decisão:** apliquei `.lower()`. Idem para `_obter_ou_criar_etiquetas_nota` (a rota `editar` também faz `.lower()` em etiquetas).

### 5. Pontos menores / observações (não bloqueantes)

- **`gerar_credencial` está em `FERRAMENTAS_ESCRITA`** apesar de ser stateless. É intencional no spec (conta as 10), mas obriga o utilizador a ligar o modo de execução só para gerar uma password. **A confirmar** se é o comportamento desejado.
- **`atualizar_evento` só actualiza campos enviados** — mais permissivo que a rota (que exige sempre `data_inicio`+`data_fim`). Adequado ao caso do assistente.
- **O limite de débito conta a tentativa antes de executar**, logo os pedidos de confirmação de apagar (2 chamadas: pedir + confirmar) consomem 2 do orçamento de 10/min. Aceitável, mas a confirmar se preferes contar só execuções efectivas.
- **O histórico de sessão continua a guardar apenas `utilizador` + resposta final** (as mensagens intermédias de `tool_calls`/`tool` ficam só no `mensagens` da iteração). É o comportamento **pré-existente**, preservado — mas significa que o modelo perde o contexto dos dados consultados entre turnos. Candidato a melhoria futura.
- **`gerar_credencial` devolve um dict** (`valor`, `forca_score`, `forca_label`) e não uma string — informação extra que o LLM recebe; funcional, mas a confirmar se queres formatar a saída.

O comentário de segurança foi mantido e reforçado (docstring do módulo + `executar_ferramenta`): **o `user_id` é sempre injectado pelo caller, nunca vem do modelo** — verificado no teste de isolamento entre dois utilizadores.
---

# Correção de bug crítica — OpenRouter: HTTP 200 com corpo de erro e falha em cascade

## Problema

`processar_mensagem_assistente('cria um evento para amanhã: "Cortar cabelo" às 9 horas')` devolvia **"Não consegui gerar uma resposta"** em vez de criar o evento.

## Diagnóstico

| Modelo | Resultado |
|---|---|
| `google/gemma-4-31b-it:free` | 429 (rate limit) |
| `nvidia/nemotron-3-super-120b-a12b:free` | 502 (sobrecarregado) |
| `cohere/north-mini-code:free` | ✅ 200, `content: ''` + `tool_calls` corretos |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | ✅ idem |

Dois bugs no `app/assistente/cliente.py`:

1. **Bug A (causa raiz):** o OpenRouter devolve HTTP 200 com corpo `{"error": ...}` quando o provider upstream falha. O código original só faz `raise_for_status()` — 200 passava como sucesso — e o `contexto.py` não encontrava `choices` → mensagem de erro genérica. O evento nunca era criado.
2. **Bug B:** `resposta.raise_for_status()` estava fora do `try` — um 502/503 lançava `HTTPError` que abortava toda a cadeia de fallback, nunca chegando ao cohere que funciona.

## Correção

### `app/assistente/cliente.py`
- Adicionadas classes `RateLimitError` e `ServicoIndisponivelError`.
- Constante `_MODELOS_FALLBACK` no topo.
- Funções auxiliares: `_detalhes_erro()`, `_codigo_erro()`, `_classificar_resposta()` — esta última valida HTTP **e** corpo da resposta, distinguindo `rate_limit` / `modelo_indisponivel` / `servico` / `ok`.
- `chamar_llm()` agora: tratamento de erro no corpo HTTP 200, fallback imediato em qualquer falha de provider, backoff apenas para exceções de rede, exceções específicas no final.

### `app/assistente/contexto.py`
- Import atualizado para incluir `ServicoIndisponivelError`.
- `_registar_resposta_invalida()` para log de amostras seguras.
- Parsing defensivo: `escolhas = resposta.get('choices')` com verificação de tipo, sem `IndexError`.
- `tool_calls` com validação de tipo (`isinstance(..., list)`).
- Mensagem de assistant com `content` vazio aceite.
- `argumentos` aceita `str` ou `dict`.
- Try/except em `executar_ferramenta` com tratamento de erro.
- `ServicoIndisponivelError` tratado no ciclo.

## Validação

- `py_compile` OK nos dois ficheiros.
- **21 testes unitários offline** (`tests/test_assistente_cliente.py`, `tests/test_assistente_contexto.py`) cobrindo 429, 200+error, 502, choices=vazio, fallback bem-sucedido, execução de ferramenta, falha de ferramenta, RateLimitError, ServicoIndisponivelError, chamada de ferramenta inválida → **TODOS PASSARAM**.
- **Smoke test real** contra OpenRouter com `cohere/north-mini-code:free`: `processar_mensagem_assistente('cria um evento para amanhã: "Cortar cabelo" às 9 horas', user_id=1, modo='escrita')` devolveu `"O evento \"Cortar cabelo\" foi criado com sucesso para amanhã, 18/09/2026, das 9h às 10h. ID: 4."` e o evento foi criado na BD e posteriormente removido.

## Ficheiros alterados

- `app/assistente/cliente.py`
- `app/assistente/contexto.py`
- `tests/test_assistente_cliente.py` (novo)
- `tests/test_assistente_contexto.py` (novo)


