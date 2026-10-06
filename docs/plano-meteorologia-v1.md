# Plano técnico final — Módulo Meteorologia V1 (especificação de implementação)

> Versão consolidada após aprovação com ajustes. Open-Meteo validado com payloads reais em 06/10/2026.

## Ajustes aplicados (resumo)

1. **Sem debounce/autocomplete** — pesquisa só via botão/Enter.
2. **Sem cache na V1** — `services.py` com fronteira clara para adicionar TTL depois.
3. **`/meteorologia/` sem localização → estado vazio + botão "Definir localização"** (sem redirect obrigatório).
4. **Etapas A (Localização) e B (Previsão)** separadas, cada uma com critério de aceitação próprio.
5. **Payloads Open-Meteo confirmados** — ver §3.
6. **Mapeamento WMO em constantes no `services.py`**, sem dependências.
7. **`services.py` desacoplado** (funções puras, sem Flask) para futuro `get_meteorologia(local, data)`.
8. **Escopo congelado** — fora: dashboard global, Assistente, notificações, radar/mapas, histórico, multi-localizações, índices de atividades, `pipe_tasks.py`.

## 1. Arquitetura atual relevante (resumo verificado)

* Factory `create_app` em `app/__init__.py`; Blueprint por módulo; padrão de referência é **Combustíveis** (`bp` definido em `routes.py`, `__init__.py` só reexporta).
* Registo de módulos: `app/modulos/config.py: MODULOS_DISPONIVEIS` alimenta dashboard (`dashboard.html` já é dinâmico — **não precisa edição**) e Loja (`UserModulo` + `/modulos/api/toggle`).
* Precedente de API externa: `app/cambio/service.py` (`requests`, `timeout=8`, `try/except → None`, função pura reutilizada pelo Assistente). Mesmo molde para meteorologia.
* Sem tabela genérica de preferências — `notificacao_preferencias`, `UtilizadorConcelho`, colunas 2FA em `User` são todas específicas. Logo: tabela própria (§5).
* Frontend: `base.html` + tokens `pipe.css` (dark/light herdado), JS vanilla inline, AJAX com `'X-CSRFToken': '{{ csrf_token() }}'` + `request.get_json()`.
* Segurança: `CSRFProtect` global, `login_required`, `limiter` de `app.extensions` (com `get_remote_address` — obrigatório no PA), tudo filtrado por `user_id`.
* Testes: `create_app('testing')` obrigatório (guarda-civil em `tests/conftest.py`); mocks via `monkeypatch`, nunca rede/BD real.
* Deploy PA free: `git pull → flask db upgrade → reload`; schema só via Flask-Migrate (baseline `3b14f5bd26a5` imutável); confirmar hosts Open-Meteo com `curl` no terminal do PA antes do deploy (têm docs públicas: `open-meteo.com/en/docs`).

## 2. Decisões técnicas

1. **Open-Meteo Geocoding + Forecast** — sem chave, sem `.env`, sem `requirements.txt` novo (§3).
2. **Persistir só 1 localização/utilizador.** Previsão nunca vai à BD; na V1 é pedida ao vivo por visita à página (máx. 1 chamada externa por visita). Cache TTL fica como evolução posterior, com gancho já previsto (§8).
3. **Render server-side da previsão** (`GET` monta dicionário → Jinja); **AJAX só na pesquisa/gravação de local** (padrão Combustíveis/Câmbio).
4. **Sem redirect obrigatório**: `/meteorologia/` sem local → estado vazio + botão "Definir localização" → `/meteorologia/localizacao`.
5. **Blueprint `meteorologia`**, `url_prefix='/meteorologia'`, definido em `routes.py`.

## 3. APIs validadas (payloads reais, 06/10/2026)

**Geocoding** — `GET https://geocoding-api.open-meteo.com/v1/search?name={q}&count=5&language=pt&format=json`

Resposta confirmada: `{results: [...], generationtime_ms}`; sem resultados a chave `results` **ausenta-se** (tratar como `[]`). Campos por resultado:

| Campo | Presença | Uso V1 |
|---|---|---|
| `name` | sempre | exibição + `nome` guardado |
| `latitude`, `longitude` | sempre | guardados; usados na forecast |
| `country` | sempre | exibição + `pais` guardado |
| `admin1` (ex. "Distrito de Braga") | quase sempre | exibição + `regiao` guardada |
| `admin2`/`admin3` (concelho/freguesia) | opcionais | exibição auxiliar (`admin2` se existir); **não** guardar |
| `timezone` (ex. `Europe/Lisbon`) | sempre nos casos PT | guardada; fallback `Europe/Lisbon` |
| `id`, `elevation`, `population`, `feature_code`, `country_code`, `*_id` | metadados | **ignorar** |

Desambiguação confirmada: "Vila Verde" devolve 1.º Vila Verde–Braga (PPLA2, sede), depois Alenquer/Lisboa, Moçambique, Santarém, Leiria — a linha `admin1 + country` distingue. "Geres" devolve 1.º Gerês–Terras de Bouro–Braga. Texto de ajuda deve sugerir "Gerês, Braga" se ambíguo.

**Forecast** — `GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weathercode,wind_speed_10m,wind_direction_10m,uv_index&hourly=temperature_2m,weathercode,precipitation_probability&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=7`

Confirmado para Vila Verde:

* Topo: `latitude`, `longitude` (**snapped à grelha**, ex. pedido 41.65 → 41.67683 — normal, ignorar), `timezone: "Europe/Lisbon"`, `timezone_abbreviation`, `utc_offset_seconds`, `elevation`. Blocos `*_units` — ignorar.
* `current`: `time` (ISO local), `temperature_2m` (°C), `relative_humidity_2m` (%), `apparent_temperature` (°C), `precipitation` (mm), `weathercode` (int), `wind_speed_10m` (km/h), `wind_direction_10m` (°), `uv_index`. **Não existe** `precipitation_probability` nem máx/mín no `current`.
* `hourly`: arrays paralelos `time[]`, `temperature_2m[]`, `weathercode[]`, `precipitation_probability[]` (168 entradas = 7 dias).
* `daily`: arrays de 7: `time[]` (`YYYY-MM-DD`), `weathercode[]`, `temperature_2m_max[]`, `temperature_2m_min[]`, `precipitation_probability_max[]`.

Regras de normalização vinculativas (Etapa B):

* Prob. precipitação "atual" = `hourly.precipitation_probability[i]` no índice da hora de `current.time` (fallback: primeiro índice `>=` hora atual; se falhar, `None` → "—").
* Máx/mín "de hoje" = `daily.temperature_2m_max[0]` / `min[0]`.
* Faixa horária = 24 entradas a partir do índice da hora atual.
* Parse sempre defensivo (`.get`, `None` → "—", nunca `KeyError` → 500).

## 4. Ficheiros a criar/alterar

**Criar:**

```text
app/meteorologia/
    __init__.py        # só: from app.meteorologia.routes import bp
    models.py          # LocalizacaoMeteorologia (§5)
    services.py        # constantes + pesquisar_locais + obter_previsao_* + MAPA_WMO (§6–8)
    routes.py          # bp + 4 rotas (§9)
app/templates/meteorologia/
    localizacao.html   # Etapa A
    index.html         # Etapa B
tests/test_meteorologia.py            # Etapas A+B (§11)
migrations/versions/xxxx_*.py         # gerado por flask db migrate (Etapa A)
```

Sem `static/` próprio, sem `forms.py` (validação JSON no backend), sem tarefa em `pipe_tasks.py`.

**Alterar (só 2 ficheiros + 1 migração):**

| Ficheiro | Alteração | Porquê |
|---|---|---|
| `app/__init__.py` | registar blueprint após o de combustíveis + importar modelo no bloco `TESTING` | rotas + `create_all()` de testes |
| `app/modulos/config.py` | 1 entrada `meteorologia` em `MODULOS_DISPONIVEIS` (`nome 'Meteorologia'`, ícone `🌤️`, `url_endpoint 'meteorologia.index'`) | card dashboard + Loja automáticos |

Não tocar: `dashboard.html`, `base.html`, `pipe.css`, `pipe_tasks.py`, `assistente/*`, `.env`, `requirements.txt`.

## 5. Modelo/BD e migração (Etapa A)

Nova tabela `meteorologia_localizacao` — justificação: não há prefs genérica; estender `notificacao_preferencias` ou `User` violaria coesão/acoplamento; tabela chave-valor seria over-engineering com perda de tipagem.

* Colunas: `id` PK; `user_id` FK `utilizadores.id`, `nullable=False, unique=True` (1 local/utilizador garantido na BD); `nome` String(120); `latitude`/`longitude` Float (ambos `nullable=False`); `pais` String(80); `regiao` String(120) nullable (de `admin1`); `timezone` String(64) nullable (default `Europe/Lisbon`); `atualizada_em` DateTime utcnow/onupdate.
* Queries sempre por `current_user.id`.
* Migração: `flask db migrate -m "adiciona meteorologia_localizacao"` → rever diff → `backup_bd.py` → `upgrade` local; no PA `git pull` + `flask db upgrade`; rollback `downgrade -1`.

## 6. Mapeamento WMO (no `services.py`, sem dependências)

Dicionário `WMO = {codigo: (descricao_pt_pt, emoji)}` cobrindo 0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99 (+ fallback `None → ("—", "❔")`). Exemplos: `0 ("Céu limpo","☀️")`, `3 ("Encoberto","☁️")`, `61 ("Chuva fraca","🌦️")`, `95 ("Trovoada","⛈️")`. Função `descrever_wmo(codigo)`.

## 7. Etapa A — Localização (especificação)

**Contratos:**

* `services.pesquisar_locais(q: str) -> list[dict] | None` — pura (sem Flask): strip/valida (`2 ≤ len ≤ 100`, senão `[]`); `requests.get(GEOCODING_URL, params={name, count:5, language:'pt', format:'json'}, timeout=8, headers=User-Agent PIPE-Meteorologia/1.0)`; `raise_for_status`; `dados.get('results', [])`; normaliza cada um para `{nome, latitude, longitude, pais, regiao (admin1), detalhe (admin2), timezone}` com `.get` (admin2/3 podem faltar); exceção/timeout → `None`.
* `services.guardar_localizacao(user_id, payload) -> (ok, erro)` — pura quanto a Flask (recebe `user_id`): valida tipos/intervalos lat/lon, strings não vazias com teto; upsert pela unique (`query.filter_by(user_id)` → update ou insert); `commit` com rollback em exceção.

**Rotas A:**

* `GET /meteorologia/localizacao` (`localizacao`, `login_required`) — render `localizacao.html` (+ local atual se existir).
* `GET /meteorologia/api/pesquisar?q=` (`api_pesquisar`, `login_required`, `limiter 30/minute`) — `q` vazio → 400; `None` do serviço → 503 `{erro}`; senão 200 `{resultados}` (vazio → UI mostra "Sem resultados").
* `POST /meteorologia/api/localizacao` (`api_guardar`, `login_required`, `limiter 10/minute`, `request.get_json()`) — usa **`current_user.id`** (nunca `user_id` do cliente); inválido → 400; 200 `{ok:true}`.

**Template `localizacao.html`:** form com input + botão "Pesquisar" (submit → `fetch`, **sem debounce/autocomplete**; Enter submete); lista de resultados como botões (📍 nome + `regiao — pais` + `detalhe` se houver); clique → bloco de confirmação com resumo + botão "Confirmar localização" (`POST`); estados vazio/erro em PT-PT; classes `cartao/btn/input/texto-subtil` existentes.

**Aceitação A:** pesquisar "Vila Verde" lista ≥2 com Braga distinguível; confirmar grava 1 linha com os 7 campos; regravar substitui (não duplica); testes A passam.

## 8. Etapa B — Previsão (especificação)

**Contratos (puros, sem Flask):**

* `services.obter_previsao(lat, lon, timezone=None) -> dict | None` — 1× `requests.get(FORECAST_URL, params={...§3..., timezone:'auto'}, timeout=8)`; `raise_for_status`; parse defensivo; monta `{atual: {...11 campos...}, horaria: [...×24], diaria: [...×7], timezone, atualizada_em, fonte:'Open-Meteo'}`; exceção → `None`.
* `services.obter_previsao_utilizador(user_id) -> (payload | None, motivo)` — sem local → `(None, 'sem_localizacao')`; com local → `(obter_previsao(...), ...)`; `motivo 'api_indisponivel'` se `None`.
* **Gancho de cache (não implementar na V1):** todo o acesso à Forecast API fica **dentro** de `obter_previsao`, assinatura estável `(lat, lon, timezone)`. Evolução futura = wrapper interno com dict `{chave: (ts, payload)}` + TTL, sem tocar rotas/templates/testes. Documentar em comentário no `services.py`.

**Rota B:**

* `GET /meteorologia/` (`index`, `login_required`) — sem local → render `index.html` em **estado vazio** (texto + botão "Definir localização" → `url_for('meteorologia.localizacao')`); com local e API ok → render com `previsao`; com local e API em baixo → render com `erro` amigável (200, nunca 500).

**Template `index.html`:** cabeçalho (nome, região/país, atualizada em, link "📍 Mudar localização"); cartão "agora" (temperatura grande + condição + grelha: sensação, máx/mín, prob. precip., precipitação mm, humidade %, vento km/h + direção por extenso — converter °→ ponto cardeal em `services.py` —, UV); faixa horária scroll-x (24 cards: hora, ícone, temp, prob); 7 dias (dia, ícone, máx/mín, prob); `None` → "—". Só classes/tokens existentes.

**Aceitação B:** com local definida, página mostra os 11 campos atuais + 24h + 7 dias a partir do payload real; API em baixo → mensagem amigável sem 500; campos ausentes → "—"; testes B passam.

## 9. Rotas (consolidado)

| Etapa | Método | Rota | Função | Tipo | Limite |
|---|---|---|---|---|---|
| B | `GET` | `/meteorologia/` | `index` | HTML | — |
| A | `GET` | `/meteorologia/localizacao` | `localizacao` | HTML | — |
| A | `GET` | `/meteorologia/api/pesquisar?q=` | `api_pesquisar` | JSON | 30/min |
| A | `POST` | `/meteorologia/api/localizacao` | `api_guardar_localizacao` | JSON | 10/min |

## 10. Segurança (vinculativo)

`login_required` nas 4; `current_user.id` em todas as queries (anti-IDOR); CSRF via `X-CSRFToken` nos `fetch` (+ `csrf_token()` hidden se houver form clássico); rate limits da tabela §9 (`from app.extensions import limiter`); revalidação server-side de tudo o que vem do cliente (tamanho de `q`, intervalos lat/lon, tetos de strings); `timeout=8` + `User-Agent` próprio; `app.logger.warning` sem dados do utilizador; resposta ao cliente sempre genérica em 503.

## 11. Testes (`tests/test_meteorologia.py`, `create_app('testing')`, `requests.get` mockado)

**Etapa A:** anónimo → 302 login; `q` vazio → 400; pesquisa válida (mock 2 Vila Verdes) → 200 + normalização correta (incl. `admin2` ausente → `None`); envelope sem `results` → `[]`; timeout Geocoding → 503; gravação válida → 200 + linha completa; lat fora de intervalo/tipos errados → 400 + nada gravado; regravação faz update (1 linha); isolamento A↔B total.

**Etapa B:** sem local → 200 estado vazio com botão (sem redirect); com local (mock forecast realista) → 200 com nome + temperatura + 7 dias; `current` sem `uv_index`/`apparent_temperature` → "—" sem exceção; forecast timeout/500 → 200 com mensagem de erro (sem 500); prob. atual vem da hora certa do `hourly`; máx/mín de `daily[0]`; Loja contém slug + toggle.

## 12. Deploy e docs

Pré-deploy: `curl` aos 2 hosts no terminal do PA (whitelist). Deploy com migração: `git pull → flask db upgrade → reload` + smoke (pesquisar Vila Verde → gravar → ver previsão). Pós: atualizar `Estado_Atual.md` + `CHANGELOG.md`. Sem bump de `?v=` (sem CSS global novo).

## 13. Futuro Assistente (só preparação)

Nenhuma tool agora. O desacoplamento (`pesquisar_locais`, `obter_previsao`, `obter_previsao_utilizador` puras) permite criar depois `get_meteorologia(local=None, data=None)` em `assistente/ferramentas.py` (leitura, filtrada por `user_id`, payload enxuto para o teto de 2000 chars) + 1–2 linhas no system prompt. Decisão futura: só localização guardada vs locais arbitrários (recomendação: começar pela guardada).

## 14. Sequência de implementação

**Etapa A:** `models.py` → registo import TESTING → `migrate/upgrade` → `services.pesquisar_locais + guardar_localizacao` → rotas A → registo blueprint + `MODULOS_DISPONIVEIS` → `localizacao.html` → testes A → QA A (Vila Verde/Braga/Gerês/Porto, sem resultados, lat inválida, isolamento, dark/light).

**Etapa B (só após A verde):** `services.obter_previsao* + WMO + vento cardinal` → rota `index` → `index.html` → testes B → QA B (payload real, API em baixo, campos ausentes) → `pytest` completo (regressão) → deploy → docs.

**Pós-V1 (fora deste plano):** cache TTL + stale-while-revalidate dentro de `obter_previsao` (sem alterar contratos); depois, e só depois: dashboard, Assistente, notificações.

