# Plano Técnico — Dashboard Global de Resumo dos Módulos (PIPE v1.7.0)

## 1. Enquadramento e objectivo

**Objetivo:** evoluir a dashboard (`/`, `app/templates/dashboard.html`) de um catálogo de links estáticos para um painel que apresenta, para cada módulo ativo, um resumo útil dos seus dados (contagens, estado, valores recentes), sem introduzir acoplamento forte entre módulos e sem degradar o arranque em dev/prod.

**Restrições do ambiente:**
- Deploy em **PythonAnywhere free**: CPU limitada, sem workers assíncronos. Qualquer chamada externa na renderização de página é um risco de slow/502.
- Arranque com `app.create_app()` → renderização direta. Nada de Redis, Celery ou background threads na página.
- Módulos ativos decididos por `UserModulo` (relação utilizador↔módulo); só se deve somar resumo a módulos que o utilizador tem ativos.
- **Regra de ouro:** no carregamento síncrono do dashboard (`GET /`), **apenas SQL local e serviços locais**. Nada de `requests`, `urllib`, threads, asyncio ou gevent.

**Não se deve:** chamar APIs externas (Wise, Open-Meteo, API Aberta/Combustíveis, pedromealha) dentro do fluxo síncrono da dashboard; duplicar a mesma lógica de resumo no dashboard e no Assistente.

---

## 2. Estado actual (confirmado por auditoria)

### `MODULOS_DISPONIVEIS` — `app/modulos/config.py`
Dicionário de **capacitação**, não de dados. Cada entrada só traz `nome`, `icone`, `url_endpoint`, `descricao`. É um *mapa de rotas*, não um catálogo auto-descritivo. Ordem fixa: `euromilhoes, tarefas, notas, passwords, cambio, cores, conversoes, assistente, calendario, combustiveis`.

### Módulo `modulos`
- `UserModulo` (tabela `user_modulo`: `user_id`, `modulo`, `ativo`, `data_ativacao`) + `get_modulos_ativos(user_id)` — esta é a **única fonte de verdade** sobre o que está ativo e na **qual ordem**.
- Rotas de ativar/desativar via `POST /modulos/<slug>/toggle`.
- A ordem visual dos cards no dashboard é a **mesma ordem da BD** (`get_modulos_ativos`); não há ordem secundária — **o dashboard controla a apresentação, o provider só fornece dados.**

### `dashboard.html`
Grelha de `<a>` cards simples, renderizada em `app/__init__.py::dashboard()` com `modulos_ativos` + `MODULOS_DISPONIVEIS`. Rota mais quente da app, fora do rate limit. **A nova funcionalidade deve ser additiva — o fallback sem resumo é obrigatório.**

### Assistente IA (`app/assistente/ferramentas.py`)
7 ferramentas de leitura com `user_id` injetado: `get_tarefas`, `get_notas`, `get_euromilhoes`, `get_resumo_geral`, `get_eventos`, `get_cambio`, `get_combustiveis`.
**Nota importante:** `get_resumo_geral(user_id)` **já existe** e faz contagens SQL idênticas ao que os providers fariam:
```python
{
    'tarefas_total': Tarefa.query.filter_by(user_id=user_id).count(),
    'tarefas_em_atraso': Tarefa.query.filter(..., concluida=False,
        data_limite.isnot(None), data_limite < hoje).count(),
    'tarefas_concluidas_hoje': ...,
    'notas_total': Nota.query.filter_by(user_id=user_id, arquivada=False).count(),
    'notas_fixadas': ...,
    'euromilhoes_jogos_total': Jogo.query.filter_by(user_id=user_id).count(),
    ... combustiveis (só se houver concelhos)
}
```
Isso significa que a **camada de agregação já existe, fragmentada no Assistente**. O provider de dashboard **deve replicar as mesmas SQLs** (garantindo consistência de números), não inventar novas regras. **Não refatorar as ferramentas do Assistente.**

### Módulos sem serviço próprio (SQL direta)
- `tarefas/` → `Tarefa(user_id, lista_id, texto, concluida, prioridade, data_limite, data_conclusao, notificada_em, texto, criado_em)`. Não há `service.py`; a SQL de "o que está a vencer" vive em `tarefas/routes.py` (`filtro in {hoje, semana, alta, concluidas}`) e é duplicada em `scripts/pipe_tasks.py`.
- `calendario/` → `Evento(user_id, titulo, descricao, localizacao, data_inicio, data_fim, dia_inteiro, cor, notificar, notificado_em, criado_em)`. API `/calendario/api/eventos` (GET) faz `filter(user_id, data_inicio >= inicio, data_inicio <= fim)`. Não há `service.py`.

### Combustíveis (`combustiveis/services.py`)
API Aberta; recolha agendada (terças). Funções: `obter_tipos_combustivel_disponiveis`, `obter_postos`, `obter_precos_para_concelhos`, `sincronizar_combustiveis`. Já armazenado localmente — **reutilizar `obter_precos_para_concelhos(user_id)`; zero chamadas externas na dashboard.**

---

## 3. Auditoria por módulo (dados relevantes + custo + decisão)

| Módulo | BD? | Resumo útil | Custo | Decisão |
|---|---|---|---|---|
| **Tarefas** | sim | totais, pendentes, em atraso (vs `data_limite`), concluídas hoje | 2–3 `COUNT` | ✅ MVP 1 — SQL idêntica a `get_resumo_geral`/`pipe_tasks` |
| **Calendário** | sim | eventos de hoje, próximos 7 dias, totais | 2–3 `COUNT` | ✅ MVP 1 — SQL da API `api_eventos` |
| **Combustíveis** | sim | preços médios nos concelhos do utilizador | SQL local | ✅ Fase 3 (2º módulo) — `obter_precos_para_concelhos` |
| **Notas** | sim | totais, checklists pendentes, fixadas | `COUNT` | ✅ Fase 3 |
| **Euromilhões** | sim (Jogo) | nº de jogos registados | SQL | ✅ Fase 3 — **apenas contagem; o cálculo de acertos é HTTP externo (API pedromealha) e fica fora do provider** |
| **Passwords** | sim | `cofre_ativo` (bool) | `COUNT` no cofre | ✅ Fase 4 — **só booleano; nunca contagem/títulos** |
| **Câmbio** | **não** | stateless (Wise + fallback) | HTTP externo | 🚫 Fora do MVP; provider `externo` se, no futuro, um lazy AJAX for aceite |
| **Cores / Conversões** | não | stateless | — | Não se resume |
| **Assistente IA** | — | stateless (LLM) | — | Sem resumo próprio nesta fase |
| **Modulos (loja)** | sim | — | — | Já é o painel de gestão |

**Meteorologia — REMOVIDA.** A pasta `app/meteorologia/` existe mas está vazia/inutilizável; não há serviços de geocoding nem dados reais. Qualquer referência a `LocalizacaoMeteorologia` / Open-Meteo / "Etapa B" deve ser descartada.

**Padrão observado:** os módulos com BD têm resumos baratos (`COUNT`). Os stateless (Câmbio) exigem rede → proibidos na renderização síncrona.

---

## 4. Arquitetura escolhida — registry explícito, providers como adaptadores

**Escolha:** um registry explícito (sem descoberta mágica), com o provider a ser um **adaptador**:

```
Provider Tarefas
        ↓
service/query existente do módulo   (SQL reutilizada de routes.py / get_resumo_geral)
        ↓
contagens / booleanos
        ↓
formato dashboard
```

**Estrutura proposta:**

```
app/
    dashboard/
        registry.py      # DASHBOARD_PROVIDERS = {"tarefas": TarefasProvider, "calendario": CalendarioProvider}
        base.py          # DashboardProvider (contrato + estado padronizado)
    tarefas/
        dashboard.py     # TarefasProvider → reutiliza SQL de tarefas/routes.py
    calendario/
        dashboard.py     # CalendarioProvider → reutiliza SQL de calendario/routes.py
```

### Contrato do provider (`dashboard/base.py`)

```python
class Estado:
    OK = "ok"
    NAO_CONFIGURADO = "nao_configurado"
    INDISPONIVEL = "indisponivel"

class DashboardProvider(Protocol):
    slug: str                       # id em MODULOS_DISPONIVEIS
    nome: str                       # exibido no card
    icone: str                      # emoji de MODULOS_DISPONIVEIS
    campos: Mapping[str, str]       # key → label amigável (ex: {"pendentes": "Pendentes"})
    def resumir(self, user_id) -> dict: ...  # {estado, metricas:[{label, valor}], ...}
```

Regras de `resumir()`:
1. Só recebe `user_id`; usa `app.db` por dentro.
2. **Nunca** faz chamadas HTTP externas — é o provider síncrono.
3. Devolve contagens/booleanos só; nada de strings longas, payloads ou dados sensíveis.
4. `Estado.NAO_CONFIGURADO` = "o utilizador ainda não tem dados configurados neste módulo" (ex: sem concelhos escolhidos).
5. Qualquer exceção interna vira `Estado.INDISPONIVEL` (trata-se no dashboard, nunca propaga).

### Registry (`dashboard/registry.py`)

Lista explícita, importada uma vez na factory:

```python
DASHBOARD_PROVIDERS = {
    "tarefas":   TarefasProvider(),
    "calendario": CalendarioProvider(),
}

def carregar_providers():
    """Chamado em create_app() para tornar o registry disponível.
    Não faz queries — só associa as classes registadas."""
    pass
```

**Não há auto-registo por import do blueprint** — é uma lista explícita e fácil de auditar/testar. Módulos sem provider ficam fora do dict e aparecem como cards simples (fallback).

### Como a dashboard usa

```python
from app.dashboard.registry import DASHBOARD_PROVIDERS, carregar_providers

def dashboard():
    ...
    resumos = {}
    for slug in modulos_ativos_slugs:            # ordem da BD / MODULOS_DISPONIVEIS
        prov = DASHBOARD_PROVIDERS.get(slug)
        if prov is None:                          # fallback: card clássico
            continue
        try:
            r = prov.resumir(current_user.id)
            resumos[slug] = r
        except Exception:                         # falha isolada
            resumos[slug] = {"estado": "indisponivel"}
            app.logger.warning(...)
    return render_template('dashboard.html',
                           modulos_ativos=modulos_ativos,
                           MODULOS_DISPONIVEIS=MODULOS_DISPONIVEIS,
                           resumos=resumos)
```

A renderização do card fica **genérica**:
- sem `resumos` (fallback de regressão) → layout antigo;
- com `resumo`: badge colorido + 1–2 números do provider;
- `nao_configurado` → card cinzento, link ativo;
- `indisponivel` → card amarelo, link de navegação mantém;
- **um provider em erro não impede a página de carregar.**

---

## 5. Integração incremental (sem quebrar o dashboard)

- **Passo 1 — infra:** criar `app/dashboard/` (registry + contrato). Nada de alterações em `MODULOS_DISPONIVEIS` nem em templates.
- **Passo 2 — template híbrido:** `dashboard.html` recebe `resumos`; se `None` → layout antigo (garantia de regressão 0%). Se presente, o provider **sobre/escreve** o conteúdo informativo do card correspondente ao seu slug (não cria grelha duplicada) — preservando ícone, link, ativar/desativar, responsividade, dark/light.
- **Passo 3 — expandir gradualmente:** um provider por PR, um módulo por vez, cada um com o seu teste.
- **Nenhuma alteração de schema** — é uma mudança de leitura/apresentação. Sem `flask db migrate`.

---

## 6. Relação com o Assistente IA

**Separação de responsabilidades:**
- **Dashboard** = leitura passiva do estado agregado (o que existe, quantos pendentes) → camada *provider*.
- **Assistente** = leitura activa (query natural) + escrita → ferramentas continuam a usar as suas SQLs atuais (`get_tarefas` com filtros, `get_combustiveis` com concelho, etc.).

**Reutilização:** o provider de dashboard reutiliza as mesmas contagens de `get_resumo_geral(user_id)` (e a regra de atraso de `scripts/pipe_tasks.py`). O objetivo é que os números batam certo nos dois sítios — não é necessário refatorar o Assistente para isso. Alteração futura na `get_resumo_geral` só seria justificada se tornasse a contagem mais barata (e.g., `COUNT` único com `CASE`), caso em que os providers ganhariam uma função partilhada no módulo correspondente.

---

## 7. Performance e resiliência (PythonAnywhere free)

**Regra:** apenas `COUNT` sem `SELECT *`, filtrado por `user_id`, sem HTTP.
- **SQL:** `Tarefa.query.filter_by(user_id=u, concluida=False).count()`, etc. Uma query por contagem; no máximo 2–3 por provider.
- **Isolamento:** `try/except` por provider — uma falha não derruba a página; log `warning` com a razão (sem expor stack trace nem detalhes de ORM).
- **Falha parcial visível:** card fica `indisponivel` em amarelo; a página inteira carrega.
- **Não usar:** threads, `asyncio`, gevent, workers. `try/except` trata exceções, **não** corta operações lentas — a solução para performance é *não fazer* o que é lento, não tentar abafá-lo.
- **Caching:** adiado. Implementar primeiro, medir (tempo de renderização de `/`), testar; só se a medição justificar.

---

## 8. UX e estados

- Card do módulo mantém ícone, nome, link (já existentes).
- Sobreposição de resumo: badge de estado + métricas definidas pelo provider (`campos`).
- Estados: `ok` (verde) | `nao_configurado` (cinzento) | `indisponivel` (amarelo).
- Sem dados nenhuns → mensagem amigável.
- Mobile/PWA: grelha CSS grid já usada; `dark/light` via variáveis CSS semânticas (`--cor-sucesso`, `--cor-aviso`, `--cor-erro`, `--cor-texto-secundario`).

---

## 9. Segurança

- `user_id` inegociável: injetado pela dashboard a partir de `current_user.id`; **nunca vem do browser**. Todas as queries filtram por `user_id`.
- **Passwords:** provider só devolve `{"cofre_ativo": bool}`. Nunca contagem, domínios ou títulos — seria vazamento.
- **Tarefas/Notas:** só contagens agregadas, nunca textos.
- **Euromilhões:** contagem de jogos (não sensível).
- **Combustíveis:** `Posto` é globais, filtrado pelos concelhos do utilizador — mesma filtragem do Assistente.
- **CSRF/Rate limit:** nada de escrita no dashboard.

---

## 10. Testes

Suite: `tests/`, 146 testes existentes, SQLite em memória (`create_app('testing')`), `conftest.py` protege contra drop da BD real.

**Novos testes (`tests/test_dashboard.py`):**
1. **Registry:** provider registado pelo slug correto; `DASHBOARD_PROVIDERS` vazio antes de o blueprint ser importado.
2. **Módulo sem provider:** dashboard renderiza card clássico — regressão.
3. **Provider + dados:** utilizador com 3 tarefas pendentes → card mostra "3 pendentes".
4. **Provider em erro:** provider lança exceção → card `indisponivel`, dashboard carrega, log warning.
5. **Dados vazios / não configurado:** utilizador sem eventos → `nao_configurado` (ou zero).
6. **Isolamento:** utilizador A não vê contagem do utilizador B.
7. **Privacidade:** resposta do provider de Passwords não contém contagem/títulos.
8. **Sem rede:** o carregamento de `/` não faz chamadas HTTP externas (test de registo de `requests`/`urllib`).
9. **Regressão de layout:** template renderiza sem parâmetro `resumos`.

**Fixtures:** `user_com_tarefas(db, n)`, `user_com_eventos(db, n)`; mock simples de provider para teste de erro. Nada de BD de ficheiro — `testing` já é em memória.

---

## 11. Roteiro de implementação

- **Fase 0 — auditoria:** concluída (esta secção do plano já regista o que foi verificado).
- **Fase 1 — corregir o plano:** esta revisão (remover Meteorologia, fixar Tarefas/Calendário, incorporar restrições).
- **Fase 2 — infraestrutura mínima:** `app/dashboard/registry.py`, `app/dashboard/base.py`, factory call `carregar_providers()`, template híbrido com fallback `resumos=None`. Sem providers ainda. Teste de regressão.
- **Fase 3 — Tarefas + Calendário:** `app/tarefas/dashboard.py`, `app/calendario/dashboard.py`. SQL reutilizada das rotas existentes e de `get_resumo_geral`. Testes 1–8. Executar os 146 testes restantes.
- **Fase 4 — avaliação:** ficheiros, testes, tempo de renderização, decisões, próximos passos. **Parar e aguardar aprovação antes de Combustíveis/Notas.**
- **Fase 5 — expansão (após aprovação):** Combustíveis (`obter_precos_para_concelhos`), Notas, Euromilhões (apenas contagem de jogos), Passwords (booleano).
- **Fase 6 — documentação:** actualizar `Estado_Atual.md` e a secção "para adicionar módulo" no CLAUDE.md — refletindo que o card é gerado genericamente e não se cria card manual em `dashboard.html`.

**Cronograma sugerido:** Fase 2+3 ~1 semana, Fase 4 em conjunto com a revisão, expansão por PRs.

---

## 12. Alerta sobre complexidade

Esta proposta **não é excessivamente complexa**: registry com ~6 linhas de interface por provider, ~15 linhas de renderização, e providers que **copiam SQL já existente** em vez de reescrever lógica. O risco real seria a opção (A) (dashboard a importar todos os módulos), que parece mais simples num PR mas cria acoplamento e duplicação. A estrutura actual da app (blueprints independentes + Assistente com tool use) exige um ponto central de agregação — e esse ponto já existe, fragmentado em `get_resumo_geral` e `scripts/pipe_tasks.py`. O plano só organiza e padroniza o que já está meio feito.

**Restrições não negociáveis (relembradas):**
- Zero referências a Meteorologia.
- Câmbio fora do MVP síncrono; sem assumir cache ou endpoint `ultima-taxa`.
- Combustíveis só lê dados locais; reutiliza `obter_precos_para_concelhos`.
- Assistente: não refatorar.
- Sem cache prematuro; medir antes de optimizar.
- Sem alterações de schema.
- Sem chamadas HTTP externas no `GET /`.
