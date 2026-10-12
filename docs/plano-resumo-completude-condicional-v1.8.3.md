# Plano — Resumo Diário v1.8.3: cobertura condicional + anti-metalinguagem

**Estado do plano:** ✅ **IMPLEMENTADO** (commit a preparar). Ver `CHANGELOG.md` [v1.8.3].
**Data:** 2026-10-12 | Projecto: PIPE v1.8.2 (commit `ba42d6f`, `main` limpa)

> **Nota de fecho:** implementado com **âmbito completo** (passos 1+2+4+5) mais uma
> frente adicional não prevista no plano — a **validação de títulos por
> palavras-chave** (ver «Frente extra» abaixo). Passo 3 (retry Open-Meteo)
> ficou opcional/fora. Diagnóstico com LLM real reproduziu ambos os bugs e
> confirmou a correcção (os 3 cenários passam agora com origem LLM, sem
> metalinguagem).

---

## 0. Contexto: o teste que motivou este plano

Pré-visualização em produção (2026-10-12, data do resumo 12/10 após a meia-noite de Lisboa) devolveu, com **Origem: LLM**:

> Bom dia! Hoje tens às 14:00 a Reunião - Filipa Quintas. Não há outros eventos agendados. Não tens tarefas registadas para hoje. Não há informações de combustíveis disponíveis. Quanto ao tempo, não há dados meteorológicos fornecidos.

## 1. Diagnóstico (confirmado por código + teste local)

| # | Conclusão | Prova |
|---|-----------|-------|
| 1 | **A meteorologia não estava nos dados de entrada — o LLM não a largou.** A validação de completude da v1.8.2 (`em_falta = numeros_normalizados(dados) - numeros_normalizados(texto)` em `app/resumo_diario/redacao.py`) exige que todos os números do input sobrevivam. Com `13–23 °C` no input, a resposta teria de conter `13` e `23` ou cairia para `deterministico (número em falta)`. Origem foi **LLM** → o input não tinha meteorologia. | Código real `redacao.py` + reprodução local: com meteorologia no input, o LLM inclui-a ou cai no fallback; nunca a larga impunemente. |
| 2 | Causa provável da ausência: **falha transitória da Open-Meteo** nesse instante. `_meteorologia_por_data()` (`app/resumo_diario/services.py`) devolve `{}` quando a API falha — e desde a v1.8.2 regista `logging.warning`, pelo que deve haver rasto no error log do PythonAnywhere. | Código real `services.py` (v1.8.2). |
| 3 | O estilo "Não há… / Não tens… / dados fornecidos" foi **causado pela regra v1.8.2** em `MENSAGEM_SISTEMA` (`app/resumo_diario/redacao.py:46`): `'- Não omitas nada: meteorologia, eventos, tarefas e combustíveis têm todos de aparecer.\n'`. É **incondicional**: com input só-com-evento, o LLM obedeceu mencionando todos os tópicos pela negativa, incluindo fuga de linguagem do prompt (*"dados meteorológicos fornecidos"*). Erro de formulação nosso, não do modelo. | Linha 46 real do ficheiro + teste `test_prompt_inclui_regras_dados_e_prazo_de_task` (`tests/test_resumo_diario_fase4.py:97`) que fixa a string `'Não omitas nada'`. |
| 4 | A data está correcta: "Hoje tens às 14:00" indica data do resumo 12/10 (Lisboa). Nada a corrigir. | `obter_data_local()` usa `Europe/Lisbon`. |

## 2. O que fazer amanhã (ordem de execução)

### Passo 0 — Confirmar a causa sem código (5 min, produção)
1. Error log do PythonAnywhere à hora do teste: procurar `[Resumo Diário] Meteorologia em falha` ou `Meteorologia sem dados`.
2. Repetir a pré-visualização; confirmar o checkbox **Meteorologia** em `/resumo-diario/definicoes`.
3. Se o warning existir → causa confirmada (API transitória); se não existir → investigar `_meteorologia_por_data()`.

### Passo 1 — Prompt: cobertura condicional (`app/resumo_diario/redacao.py`, só texto)
Substituir a linha 46 incondicional por:
- `'- Todos os tópicos PRESENTES nos dados têm de aparecer; se um tópico não está nos dados, não o menciones.\n'`
- `'- Nunca escrevas frases sobre o que falta («não há…», «sem dados», «não foi fornecido»); nunca uses as palavras «dados», «secção» ou «resumo».\n'`

Manter intactas as strings fixadas pelo teste do prompt (`'APENAS os dados'`, `'tratados como texto simples'`, `'linguagem simples e direta'`, `'rótulos de secção'`, `'por extenso'`), actualizando apenas a asserção `'Não omitas nada'` → nova formulação.

### Passo 2 — Validação anti-metalinguagem (versão estreita, recomendada)
Rejeitar respostas com `dados fornecidos` / `sem dados` / `não fornecid-` / `secção` / `seção` / `tópico` — **com os títulos isentos** (ex.: tarefa "Limpar base de dados" não pode disparar falso fallback). Bloqueia só metalinguagem; negações legítimas como "não há chuva" continuam a passar.

### Passo 3 — Robustez da meteorologia (opcional)
Retry curto/timeout explícito na chamada Open-Meteo; **não** inventar fallback com outro dia (dado errado é pior que ausência). Opcional: incluir `secoes` no JSON da pré-visualização para diagnóstico futuro.

### Passo 4 — Testes (`tests/test_resumo_diario_fase4.py`)
- input só-com-evento → resposta sem frases de ausência passa;
- resposta com "não há dados fornecidos" → fallback;
- denylist com título contendo "dados" → passa (isenção de títulos).

### Passo 5 — Docs + deploy
CHANGELOG/Estado_Atual v1.8.3, `pytest -q tests/test_resumo_diario*.py`, commit + push; no PythonAnywhere: `git pull` → Reload (**sem alteração de BD**).

## 3. Decisão em aberto
Âmbito: **completo** (passos 1+2+3+4+5) ou **essencial** (1+4+5)? Decidir antes de implementar.

## 4. Frente extra descoberta no diagnóstico (implementada)

O diagnóstico com LLM real revelou um **segundo bug não previsto**: a
validação de títulos exigia a frase literal (`titulo.casefold() in texto`),
pelo que uma resposta **excelente** (cenário completo com todos os números e
PT-PT correctos) era rejeitada por `título em falta` só porque o LLM reescreve
«Comprar pão»/«Reunião - Filipa Quintas» em prosa natural («comprar pão»,
«uma reunião com a Filipa Quintas»). Este era o problema mais grave em
produção — o texto bom caía sempre no determinístico.

**Correcção:** a verificação passa a exigir as **palavras-chave** do título
(stopwords PT — de, com, o, ao… — não contam), com fallback para a ocorrência
literal quando o título é só stopwords. Implementado em `validar_resposta()`
com `_palavras_chave()`. Testes: `test_titulo_reescrito_em_prosa_passa`,
`test_titulo_realmente_ausente_cai`.

## 5. Resultado (validação com LLM real)

`tests/temp_modelos/diagnostico_llm_resumo.py` (untracked). Os 3 cenários
passam agora todos com **origem LLM** e sem metalinguagem:
- **A** só-com-evento → passa (antes: metalinguagem + rejeição).
- **B** completo → passa, todos os números e PT-PT preservados (antes: rejeitado por título em falta).
- **C** só-meteorologia → passa, focado só no que existe (antes: metalinguagem).
Suite integral do projecto: **322 passed** (+ 26 subtests), sem regressões.
