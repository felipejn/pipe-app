=== RELATORIO DE TESTE TEMPORARIO (PT-PT) ===
Data: 2026-10-09 (3ª execucao — 403 removido, lista final)
Fonte: tests/temp_modelos/ (2 ficheiros temporarios; 0 existentes alterados)
Prompt: "Quais as tarefas pendentes para hoje? Responde de forma concisa."
Chave: OPENROUTER_API_KEY de .env (nao alterado)

=== RESULTADOS FINAIS (6 modelos, ordenados por qualidade/tempo) ===

| # | Modelo | Tempo | Estado | Resposta (resumo) |
|---|--------|-------|--------|--------------------|
| 1 | cohere/north-mini-code:free | 1.26s | OK | Resposta util (pede mais info) |
| 2 | nvidia/nemotron-3-super-120b-a12b:free | 3.62s | OK | Resposta contextualizada |
| 3 | liquid/lfm-2.5-2.6b:free | 3.86s | OK | Resposta generica |
| 4 | dots-studio/dots-3-note-preview:free | 9.20s | OK | Resposta contextualizada |
| 5 | nvidia/nemotron-3-ultra-550b-a55b:free | 0.45s | OK | Resposta vazia |
| 6 | poolside/laguna-s-2.1:free | 0.23s | 429 | Rate limit (temporario?) |

ESTATISTICAS:
- Tempo medio (modelos OK com resposta): 4.49s
- Tempo minimo com resposta util: 1.26s (cohere/north-mini-code)
- Qualidade (resposta nao vazia): 4/6

=== DECISAO ===

Novo default: cohere/north-mini-code:free (1.26s, resposta util)
Fallbacks (por ordem):
  1. nvidia/nemotron-3-super-120b-a12b:free (3.62s, bom)
  2. liquid/lfm-2.5-2.6b:free (3.86s, generico)
  3. dots-studio/dots-3-note-preview:free (9.20s, lento mas bom)
  4. poolside/laguna-s-2.1:free (429, mas pode funcionar alternadamente)

Removidos definitivamente:
  - inclusionai/ling-3.0-flash-sante:free (404)
  - nvidia/nemotron-3-ultra-550b-a55b:free (resposta vazia)
  - thinkingmachines/inkling-small:free (403)
  - meta-llama/llama-3-8b-instruct:free (404)
  - qwen/qwen-2.5-7b-instruct:free (404)
  - google/gemma-2-9b-it:free (404)
  - mistralai/mistral-7b-instruct:free (404)
  - nvidia/nemotron-mini-4b-instruct:free (400)

=== NOTA ===
Resultados variam entre execucoes (rate limits, estado do provider).
3 execucoes realizadas — decisao baseada em consistencia observada.