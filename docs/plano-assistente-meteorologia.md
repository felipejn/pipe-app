# Plano — Integrar o módulo de Meteorologia no Assistente IA

**Estado do plano:** em revisão — aprovado com alterações decorrentes da verificação do código real.
**Data:** 2026-10-07 | Projecto: PIPE v1.7.0

## Verificações (Passo 0 — confirmado no código real do projecto)

| # | Item verificado | Resultado |
|---|-----------------|-----------|
| 1 | `app/meteorologia/models.py`: modelo, tabela e campos | ✅ **Confirmado.** Modelo `LocalizacaoMeteorologia(db.Model)`, tabela `meteorologia_localizacao`, campos: `id` (PK), `user_id` (FK `utilizadores.id`, `unique=True`, `nullable=False`), `nome` (String 120), `latitude` (Float), `longitude` (Float), `pais` (String 80), `regiao` (String 120, nullable), `timezone` (String 64, default `'Europe/Lisbon'`), `atualizada_em` (DateTime). ❌ **Difere do plano:** não existem campos `lat`/`lon`; os nomes reais são `latitude` e `longitude`. |
| 2 | `app/meteorologia/services.py`: `obter_previsao_utilizador` e helpers | ✅ `obter_previsao_utilizador(user_id)` retorna `(payload | None, motivo)` com `motivo` em `{'ok', 'sem_localizacao', 'api_indisponivel'}`. `obter_previsao(lat, lon)` existe. Helpers: `descrever_wmo(c)` → `(descricao_pt, emoji)`; `direcao_cardinal(graus)` → `'Norte'/'Nordeste'/'Este'/'Sudeste'/'Sul'/'Sudoeste'/'Oeste'/'Noroeste'`; `_num(valor)` → `None` se `None`/`bool`, senão `float(valor)`. |
| 3 | Chaves reais do payload de previsão | ✅ Root: `atual`, `horaria`, `diaria`, `timezone`, `atualizada_em`, `fonte`. `atual`: `hora`, `temperatura`, `sensacao_termica`, `humidade`, `precipitacao`, `probabilidade_precipitacao`, `codigo_wmo`, `vento_velocidade`, `vento_direcao_graus`, `uv`, `temp_max_hoje`, `temp_min_hoje`, `descricao_pt`, `emoji`, `vento_direcao_cardinal`. `horaria[n]`: `hora`, `temperatura`, `codigo_wmo`, `descricao_pt`, `emoji`, `prob_precipitacao`. `diaria[n]`: `data`, `codigo_wmo`, `descricao_pt`, `emoji`, `temp_max`, `temp_min`, `prob_precipitacao`. ❌ **Difere do plano:** a chave é `prob_precipitacao` (nunca `prob_precipitacao_max`). O payload **não transporta** `nome`/`pais`/`regiao` — só `timezone`/`atualizada_em`/`fonte`. |
| 4 | `app/assistente/contexto.py`: `_serializar_resultado_tool` | ✅ (a) usa `ensure_ascii=False`; ✅ (b) a chave `truncado` surge no JSON via `_truncar_listas` (marca `truncado: True` ao cortar a primeira lista); ✅ (c) degradação `LIMITES_ITENS_DEGRADACAO = (LIMITE_ITENS_LISTA_TOOL, 8, 5, 3, 1)` = **(10, 8, 5, 3, 1)**, com `LIMITE_CHARS_TOOL_RESULT = 2000`; aplica-se recursivamente a **todas as listas** do dict (qualquer profundidade). ❌ **Difere do plano:** o plano dizia "10→8→5→3"; são **10→8→5→3→1** (5 patamares). |
| 5 | Última versão e contagem de testes | ✅ Últimas entradas do CHANGELOG: `[v1.7.0]` e `[v1.7.1]` (ambas 2026-10-07) — **não existe v1.7.2**; a nova entrega será a **v1.7.2**. `pytest --collect-only -q` → **196 testes** (o plano dizia "182+"). |
| 6 | Estilo dos testes | ✅ `tests/test_assistente_combustiveis.py` (ferramentas) usa **unittest** (`from unittest import TestCase`, `class _BaseX(TestCase)`, `setUp`, `self.assertEqual`). `tests/test_meteorologia.py` (módulo) usa pytest. O ficheiro de combustíveis **não mocka HTTP** (usa a BD em memória real); aqui é necessário mockar a chamada à Open-Meteo → `unittest.mock.patch('app.meteorologia.services.requests.get')`. |
| 7 | Tom das mensagens de erro (`ferramentas.py`) | ✅ PT-PT formal e conciso, **sem exclamações**, `→` para caminhos de UI. Exemplos: `f'Data inválida: "{data}". Usa o formato AAAA-MM-DD.'`, `'Ainda não escolheste nenhum concelho. Vai a Combustíveis → Definições, ...'`, `'Não foi possível obter a cotação de momento. Tenta novamente mais tarde.'`, `'Ferramenta desconhecida: {nome_ferramenta}'`. |
| 8 | Medição real do tamanho do JSON (payload realista Open-Meteo, `ensure_ascii=False`) | ✅ Compacto (`local`+`atual`+`diaria`×7+`meta`): **1474 chars** (≤ 2000). Detalhado (`local`+`atual`+`horaria`×24+`meta`): **3839 chars** (> 2000 → truncador degrada `horaria` para 10 itens = 1887 chars). Detalhado c/ horaria reduzida (12h, de 2 em 2h): **1914 chars** (≤ 2000). Detalhado c/ horaria 24h + `diaria`: 4912 chars (❌ inaceitável). |

## 1. Objetivo

Permitir que o Assistente IA responda perguntas do tipo "Que tempo faz hoje?", "Vai chover amanhã?", "Qual a temperatura máxima?" consultando a previsão Open-Meteo da **localização guardada** pelo utilizador no módulo de Meteorologia, sem alterar o esquema de BD (usa a tabela `meteorologia_localizacao`, já criada na migration `c420a200f2f2`).

## 2. Padrão a seguir (conforme os outros 7 `get_*`)

| Elemento | Localização | O que fazer |
|---|---|---|
| Função executável | `app/assistente/ferramentas.py` | `get_meteorologia(user_id, detalhado=False)` |
| Definição JSON (OpenAI) | `app/assistente/ferramentas.py` | Entrada na lista `DEFINICOES_FERRAMENTAS_LEITURA` |
| Mapa nome→função | `app/assistente/ferramentas.py` | Entrada em `REGISTO_FERRAMENTAS` |
| Capacidades no prompt | `app/assistente/contexto.py` | Mencionar meteorologia em `SYSTEM_PROMPT_LEITURA` e `SYSTEM_PROMPT_ESCRITA` |
| Testes | `tests/test_assistente_meteorologia.py` | Novo ficheiro (padrão `test_assistente_combustiveis.py`) |
| Documentação | `CHANGELOG.md` + `Estado_Atual.md` | Nova entrada de versão |

Segurança já existente: `_serializar_resultado_tool()` em `contexto.py` aplica corte estrutural de listas (→ 10 itens, degrada para 8/5/3/1) e tecto duro de **2000 chars** (`LIMITE_CHARS_TOOL_RESULT = 2000`). A nova ferramenta fica protegida por esta rede sem qualquer esforço extra.

## 3. Design da nova ferramenta

### 3.1 Assinatura

```python
def get_meteorologia(user_id, detalhado=False):
    """Consulta a previsão meteorológica da localização guardada pelo utilizador.
    Ferramenta de leitura. Requer localização definida em Meteorologia;
    sem localização → erro orientador para o módulo. API indisponível → erro amigável.
    """
```

- `user_id` — obrigatório, injetado pelo despachante, filtrado por `user_id` (anti-IDOR, padrão inegociável).
- `detalhado` — opcional, `False` por defeito. `False` → resumo compacto; `True` → previsão horária reduzida.

### 3.2 Via única de obtenção de dados

**Via escolhida: query directa à tabela + `obter_previsao(lat, lon)`.**

1. `obter_previsao_utilizador` é apenas uma wrapper que repete a query de localização; chamá-la faria uma segunda query ao modelo e duplicaria a lógica de obtenção que já está em `obter_previsao`.
2. O bloco `local` fica completo e correcto directamente do modelo (`nome`, `pais`, `região`, `timezone`), enquanto o payload da previsão não transporta estes metadados.

```python
local = LocalizacaoMeteorologia.query.filter_by(user_id=user_id).first()
if local is None:
    return {'erro': 'Defina primeiro a localização em Meteorologia → '
                    'Definir localização e volte a perguntar.'}

previsao = services.obter_previsao(local.latitude, local.longitude)
if previsao is None:
    return {'erro': 'Serviço de previsão meteorológica indisponível de momento. '
                    'Tenta novamente mais tarde.'}
```

### 3.3 Payload compacto (padrão)

`local` + `atual` (campos seleccionados) + `diaria` (7 dias) + `meta`. **Removidos** `hoje` e `amanha` (duplicavam `diaria[0]` e `diaria[1]`).

```json
{
  "local":   {"nome": "Vila Verde", "pais": "Portugal",
              "regiao": "Distrito de Braga", "timezone": "Europe/Lisbon"},
  "atual":   {"temperatura": 12.4, "sensacao_termica": 10.8,
              "condicao": "Nublado", "emoji": "☁️",
              "humidade": 82, "prob_precipitacao": 40,
              "vento": {"velocidade": 14.2, "direcao_cardinal": "Oeste"},
              "uv": 0.0, "precipitacao": 0.0},
  "diaria":  [{"data": "2026-10-07", "condicao": "Nublado", "emoji": "☁️",
               "temp_max": 14.0, "temp_min": 8.0, "prob_precipitacao": 40}],
  "meta":    {"atualizada_em": "2026-10-07T22:00", "fonte": "Open-Meteo"}
}
```

Campos usados:

- `local`: `nome`, `pais`, `regiao` (String 120, nullable), `timezone` — do modelo;
- `atual`: `temperatura` (1 casa), `sensacao_termica` (1 casa), `condicao` (PT), `emoji`, `humidade` (inteiro), `prob_precipitacao` (inteiro), `vento` (`velocidade` 1 casa, `direcao_cardinal` PT), `uv` (inteiro), `precipitacao` (1 casa);
- `diaria[n]`: `data`, `condicao`, `emoji`, `temp_max` (1 casa), `temp_min` (1 casa), `prob_precipitacao` (inteiro);
- `meta`: `atualizada_em`, `fonte`.

**Arredondamento (`_num`):** humidade, probabilidades e UV → inteiro; temperaturas e velocidade do vento → 1 casa decimal (`round(x, 1)`).

**`emoji`: mantido.** Com `ensure_ascii=False` custa ~4 bytes/ocorrência no JSON e é útil para o modelo e para renderização; remover não traria benefício mensurável.

Tamanho medido do payload serializado: **1474 chars** (cabe em 2000 sem degradação).

### 3.4 Payload detalhado

`detalhado=True` devolve o mesmo, **sem `diaria`**, adicionando `horaria` reduzida: **próximas 12 horas, de 2 em 2 horas** (12 itens = 1914 chars, ≤ 2000, sem degradação). A `diaria` é excluída de propósito: assim a degradação de listas nunca afecta a previsão diária, que é a informação mais relevante.

```json
{
  "local":   {"nome": "Vila Verde", "pais": "Portugal",
              "regiao": "Distrito de Braga", "timezone": "Europe/Lisbon"},
  "atual":   {...},
  "horaria": [{"hora": "2026-10-07T22:00", "temperatura": 12.4,
               "condicao": "Nublado", "emoji": "☁️", "prob_precipitacao": 40},
              ... até 12 itens ...],
  "meta":    {"atualizada_em": "2026-10-07T22:00", "fonte": "Open-Meteo"}
}
```

**Definição JSON (como `get_combustiveis`):**

```json
{
  "type": "function",
  "function": {
    "name": "get_meteorologia",
    "description": "Devolve a previsão do tempo (atual + 7 dias) da localização guardada pelo utilizador em Meteorologia. Usar detalhado=True apenas quando o utilizador pedir a previsão horária.",
    "parameters": {
      "type": "object",
      "properties": {
        "detalhado": {
          "type": "boolean",
          "description": "Se True, devolve também a previsão horária reduzida (próximas 12 horas, de 2 em 2 horas), sem a previsão diária."
        }
      }
    }
  }
}
```

**Registo:** `'get_meteorologia': 'get_meteorologia'` em `REGISTO_FERRAMENTAS`.

## 4. Alterações file-by-file

### `app/assistente/ferramentas.py` (~+130 linhas)

1. Import no topo: `from app.meteorologia.models import LocalizacaoMeteorologia` e `from app.meteorologia import services as meteorologia_services`
2. Função `get_meteorologia(user_id, detalhado=False)` com docstring `Args`/`Returns`
3. Helpers privados `_previsao_compacta(previsao, local)` e `_previsao_detalhada(previsao, local)` — **mesma assinatura**, **ambas** devolvem o bloco `local`
4. Entrada na `DEFINICOES_FERRAMENTAS_LEITURA` (antes do `]` que encerra a lista, após `get_cambio`)
5. Entrada no mapa `REGISTO_FERRAMENTAS` (após `'get_combustiveis'`)

### `app/assistente/contexto.py` (+2 linhas)

- `SYSTEM_PROMPT_LEITURA`: na lista CAPACIDADES adicionar:
  `- Meteorologia: consultar a temperatura e a previsão do tempo da tua localização guardada.\\n`
  (após `- conversões de moeda, preços de combustíveis nos concelhos do utilizador e resumo geral do utilizador`)
- Acrescentar regra: **a ferramenta devolve apenas a localização guardada**; se o utilizador perguntar por outra localidade, o assistente deve dizê-lo e não reutilizar os dados.
- `SYSTEM_PROMPT_ESCRITA`: actualizar a lista de consultas para incluir "meteorologia":
  `- Podes consultar câmbios, meteorologia (previsão do tempo da tua localização guardada), preços de\\n`
  `  combustíveis nos teus concelhos, além de consultar E EXECUTAR ACÇÕES nos módulos Tarefas, Notas,\\n`
  `  Calendário e Passwords.\\n`

### `tests/test_assistente_meteorologia.py` (novo, ~14 testes)

Padrão `unittest` + `create_app('testing')` (como `test_assistente_combustiveis.py`), com `unittest.mock.patch('app.meteorologia.services.requests.get')` para mockar a Open-Meteo.

| Classe de teste | Casos |
|---|---|
| `RegistoFerramentaTests` | `test_registrada_no_registo_e_nas_definicoes_de_leitura`, `test_definicao_expoe_parametro_detalhado`, `test_despachante_aceita_o_filtro` |
| `SemLocalizacaoTests` | `test_sem_localizacao_retorna_erro_orientador` |
| `PrevisaoTests` | `test_previsao_retorna_payload_compacto_com_todos_os_campos`, `test_payload_enxuto_sem_campos_excessivos`, `test_api_indisponivel_retorna_erro_amigavel` |
| `DetalhadoTests` | `test_payload_detalhado_inclui_horaria_reduzida`, `test_diaria_ausente_no_detalhado` |
| `TamanhoTests` | `test_payload_compacto_cabe_no_tecto`, `test_payload_detalhado_cabe_no_tecto` |
| `IsolamentoTests` | `test_isolamento_utilizador_outro_user_sem_localizacao` |
| `FrescuraTests` | `test_meta_inclui_fonte_e_data` |

### CHANGELOG.md

Entrada **v1.7.2 — Assistente IA + Meteorologia** (ferramenta `get_meteorologia`, payload compacto/detalhado, prompts actualizados, ~14 testes). Nota de deploy: *Sem alteração de BD — no PythonAnywhere: push + Reload.*

### Estado_Atual.md

Actualizar (todos os sítios):

1. Árvore do projecto, `assistente/ferramentas.py`: "7 funções de leitura" → "8 funções de leitura"
2. Secção "Assistente IA" → "Ferramentas (ferramentas.py)": alargar a lista de leitura (`get_meteorologia`) e a contagem para 8 de leitura
3. Secção "Testes": "182 testes" → "196 testes"
4. (Se houver secção específica de Assistente IA nas ferramentas) — adicionar linha sobre `get_meteorologia`

### Typos corrigidos

- "Capabilidades" → "Capacidades"
- "Descriver" → "Descrever"
- "localizaçào" → "localização"

## 5. Código esperado (esqueleto pronto a implementar)

```python
# ferramentas.py

def _num_redondido(v, casas=1):
    """Wrapper de services._num com arredondamento (casas >= 0)."""
    v = services._num(v)
    if v is None:
        return None
    return round(v, casas)


def _previsao_compacta(previsao, local):
    """Constrói o payload compacto (~1474 chars) enviado ao modelo."""
    atual = previsao.get('atual') or {}
    diaria = previsao.get('diaria') or []
    return {
        'local': {
            'nome': local.nome,
            'pais': local.pais,
            'regiao': local.regiao,
            'timezone': local.timezone,
        },
        'atual': {
            'temperatura': _num_redondido(atual.get('temperatura'), 1),
            'sensacao_termica': _num_redondido(atual.get('sensacao_termica'), 1),
            'condicao': atual.get('descricao_pt'),
            'emoji': atual.get('emoji'),
            'humidade': _num_redondido(atual.get('humidade'), 0),
            'prob_precipitacao': _num_redondido(atual.get('probabilidade_precipitacao'), 0),
            'vento': {
                'velocidade': _num_redondido(atual.get('vento_velocidade'), 1),
                'direcao_cardinal': atual.get('vento_direcao_cardinal'),
            },
            'uv': _num_redondido(atual.get('uv'), 0),
            'precipitacao': _num_redondido(atual.get('precipitacao'), 1),
        },
        'diaria': [
            {
                'data': d.get('data'),
                'condicao': d.get('descricao_pt'),
                'emoji': d.get('emoji'),
                'temp_max': _num_redondido(d.get('temp_max'), 1),
                'temp_min': _num_redondido(d.get('temp_min'), 1),
                'prob_precipitacao': _num_redondido(d.get('prob_precipitacao'), 0),
            }
            for d in diaria
        ],
        'meta': {
            'atualizada_em': previsao.get('atualizada_em'),
            'fonte': previsao.get('fonte'),
        },
    }


def _previsao_detalhada(previsao, local):
    """Constrói o payload detalhado (~1914 chars): local + atual + horaria reduzida."""
    atual = previsao.get('atual') or {}
    horas = previsao.get('horaria') or []
    return {
        'local': {
            'nome': local.nome,
            'pais': local.pais,
            'regiao': local.regiao,
            'timezone': local.timezone,
        },
        'atual': {
            'temperatura': _num_redondido(atual.get('temperatura'), 1),
            'sensacao_termica': _num_redondido(atual.get('sensacao_termica'), 1),
            'condicao': atual.get('descricao_pt'),
            'emoji': atual.get('emoji'),
            'humidade': _num_redondido(atual.get('humidade'), 0),
            'prob_precipitacao': _num_redondido(atual.get('probabilidade_precipitacao'), 0),
            'vento': {
                'velocidade': _num_redondido(atual.get('vento_velocidade'), 1),
                'direcao_cardinal': atual.get('vento_direcao_cardinal'),
            },
            'uv': _num_redondido(atual.get('uv'), 0),
            'precipitacao': _num_redondido(atual.get('precipitacao'), 1),
        },
        'horaria': [
            {
                'hora': h.get('hora'),
                'temperatura': _num_redondido(h.get('temperatura'), 1),
                'condicao': h.get('descricao_pt'),
                'emoji': h.get('emoji'),
                'prob_precipitacao': _num_redondido(h.get('prob_precipitacao'), 0),
            }
            for h in horas[:24:2]   # próximas 12 horas (índices 0, 2, ..., 22), de 2 em 2
        ],
        'meta': {
            'atualizada_em': previsao.get('atualizada_em'),
            'fonte': previsao.get('fonte'),
        },
    }


def get_meteorologia(user_id, detalhado=False):
    """Consulta a previsão meteorológica da localização guardada pelo utilizador.

    Ferramenta de leitura. Requer que o utilizador tenha definido uma localização
    em Meteorologia → "Definir localização"; sem localização guardada devolve um
    erro orientador (o modelo encaminha para o módulo, nunca inventa dados).
    """
    # Via única: query directa + obter_previsao(lat, lon).
    local = LocalizacaoMeteorologia.query.filter_by(user_id=user_id).first()
    if local is None:
        return {
            'erro': 'Defina primeiro a localização em Meteorologia → '
                    'Definir localização e volte a perguntar.',
        }

    previsao = services.obter_previsao(local.latitude, local.longitude)
    if previsao is None:
        return {'erro': 'Serviço de previsão meteorológica indisponível de momento. '
                        'Tenta novamente mais tarde.'}

    if detalhado:
        return _previsao_detalhada(previsao, local)
    return _previsao_compacta(previsao, local)
```

## 6. Validação e smoke test

1. **Unitários:** `pytest tests/test_assistente_meteorologia.py -v` + suite completa `pytest -q` (regressão, 196 testes).
2. **Smoke offline:** serializar com `_serializar_resultado_tool(r)` e medir `len()` do resultado — com API mockada, `assert len(r) <= 2000` em compacto (7 dias) e em detalhado (12h reduzida); `assert 'erro' not in r`.
3. **Smoke real de tool use:** enviar "Que tempo faz hoje?" (com localização definida no teste) e verificar a tool call correcta; **caso negativo**: "Que tempo faz em Lisboa?" — o assistente não apresenta os dados guardados como sendo de Lisboa; confirma-se a regra do prompt (só a localização guardada).
4. **Revisão manual do diff** — o bloco `DEFINICOES_FERRAMENTAS_LEITURA` é sensível a chaves de fecho; garantir JSON válido e import correcto no topo (`python -c "from app.assistente import ferramentas"`).

## 7. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Payload excede 2000 chars | Decisão tomada: compacto medido = 1474 chars e detalhado medido = 1914 chars (horaria reduzida, sem `diaria`); nenhum excede o tecto → sem degradação |
| Payload com campos excessivos | Helpers com selecção explícita de campos; teste `test_payload_enxuto` valida o conjunto de chaves |
| Import circular assistente ↔ meteorologia | Import directo no topo (meteorologia só depende de `app.db` + `requests`); em caso de erro, importar dentro da função |
| Modelo não invocar a ferramenta | Prompts actualizados em ambos os modos + smoke test de tool use a validar |
| Modelo apresenta dados de outra localidade | Regra no system prompt + smoke caso negativo ("Que tempo faz em Lisboa?") |

## 8. Alternativas consideradas (decisões)

1. **Reutilizar `get_resumo_geral` em vez de nova ferramenta** — REJEITADA: `get_resumo_geral` é barato e local à BD e passaria a depender de HTTP externo (latência/falhas/rate limit); o tecto de 2000 chars já está apertado desde as v1.4.12 e v1.5.5. (Alternativa mantida como evolução futura, remeter para o provider de dashboard — sem HTTP na renderização — v1.7.4+.)
2. **Ferramenta de escrita `definir_localizacao_meteorologia(lat, lon)`** — REJEITADA neste deploy: requer confirmação explícita da localização do utilizador (UX do módulo), expor coordenadas brutas ao modelo é frágil e a rota `POST /meteorologia/api/localizacao` já faz essa gravação com validação. Deixada como evolução v1.7.3+ (com `confirmacao_necessaria`).
3. **Usar só `obter_previsao_utilizador(user_id)`** — REJEITADA: faria uma query DB adicional em duplicação com a query necessária para o bloco `local`, sem benefício (o retorno não inclui `nome`/`pais`/`regiao`).

## 9. Notas de deploy

- **Nenhuma alteração de BD** — a ferramenta lê a tabela `meteorologia_localizacao` (já criada pela migration `c420a200f2f2` do módulo Meteorologia).
- **PythonAnywhere:** `git pull` → `pip install -r requirements.txt` → **Reload** da aplicação. Validar `flask db check` (limpo) e a suite `pytest -q`.
- **Não é necessário** `flask db upgrade` nem scripts manuais.

## 10. Próximos passos / evolução futura

1. v1.7.2 (este plano): ferramenta de leitura `get_meteorologia` + testes + doc.
2. v1.7.3+: ferramenta de escrita `definir_localizacao_meteorologia` + `apagar_localizacao_meteorologia` com fluxo de confirmação (`confirmacao_necessaria`).
3. v1.7.4+: provider de dashboard (`app/meteorologia/dashboard.py`) para mostrar o tempo no dashboard principal (padrão Tarefas/Calendário) — sem HTTP externo na renderização.