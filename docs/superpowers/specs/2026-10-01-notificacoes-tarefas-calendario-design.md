# Spec — Notificações de Tarefas (vence hoje + atraso) e de Eventos do Calendário (dia anterior + dia)

**Data:** 2026-10-01
**Estado:** aprovado pelo utilizador (plano aprovado em act mode)
**Versão resultante:** v1.5.8

## Contexto actual

- A única scheduled task é `scripts/pipe_tasks.py`, corre **1×/dia no PythonAnywhere às 07:00** (hora confirmada pelo utilizador; o docstring do script dizia 23:00 e `Estado_Atual.md` dizia 08:00 — ambos errados, a corrigir).
- `tarefa_tarefas()` só notifica quando o prazo **já passou** (`data_limite < hoje`), diariamente enquanto persistir, com dedupe por `Tarefa.notificada_em` (Date; NULL = nunca notificada; `< hoje` = volta a notificar).
- `tarefa_calendario()` **não existe** — está listada como pendente (`Estado_Atual.md:336`, `:598`). O modelo `Evento` já tem `notificar` (Boolean) e `notificado_em` (Date), e a rota PUT e o assistente já fazem `notificado_em = None` ao editar (reabre a janela).
- `notification_service.send(user, type, subject, body, data)` despacha para os canais activos (Telegram/email) consoante `UserNotificationPreferences` — o serviço já filtra internamente, os chamadores não precisam de verificar canais.

## Decisões do utilizador

1. **Tarefas:** avisar **no dia do prazo** e depois **em todos os dias de atraso** até concluir/adiar.
2. **Calendário:** avisar **no dia anterior** e depois **no dia** do evento.
3. **Fora de âmbito (explícito):** toggle de preferências em `/definicoes` para eventos/tarefas; aviso na criação de tarefa com prazo para hoje.

## Design

### 1. `tarefa_tarefas()` — alargue do filtro

```python
# antes:  Tarefa.data_limite < hoje
# depois: Tarefa.data_limite <= hoje
```

- Dedupe **inalterada**: `notificada_em IS NULL OR notificada_em < hoje` → no dia do prazo envia uma vez; nos dias seguintes envia como atraso, uma vez por dia.
- Semântica do campo: `notificada_em` passa a significar "última notificação (vencimento ou atraso)" — **sem migração de BD**.
- **Mensagem única por utilizador** com secções opcionais:
  - `⏰ Vencem hoje:` (tarefas com `data_limite == hoje`)
  - `⚠ Em atraso:` (tarefas com `data_limite < hoje`, com nº de dias)
  - Assunto: `⏰ N tarefas com prazo hoje e M em atraso no PIPE` (ou uma só secção quando a outra está vazia).
- `type` passa de `tarefa_atraso` para `tarefa_lembrete` (só usado no script; sem referências noutro lado); `data={'total_hoje': n1, 'total_atraso': n2}`.
- *Edge aceite:* tarefa criada com prazo para hoje **depois das 07:00** só é avisada no dia seguinte (como atraso).

### 2. `tarefa_calendario()` — nova função, registada em `TAREFAS`

No dia D, para cada evento com `notificar == True` e (`notificado_em IS NULL OR notificado_em < D`):

- **Dia anterior:** `date(data_inicio) == D+1` → "📅 Amanhã: …"
- **Próprio dia:** `date(data_inicio) == D` **e** (`dia_inteiro == True` **ou** `data_inicio > datetime.now()`) → "📅 Hoje: …"
- Eventos **já iniciados** às 07:00 (não dia inteiro) são ignorados — nunca mais voltam a casar com as condições de data.
- Depois de enviar: `notificado_em = D` (por evento) → sequência real: D−1 envia "amanhã", D envia "hoje", D+1 nada. **Um único campo Date cobre os dois avisos — sem migração de BD.**
- **Agrupado por utilizador** (uma mensagem com todos os eventos do utilizador, secções "Amanhã"/"Hoje"); ordenado por `data_inicio`; `type='evento_lembrete'`.
- Apenas `data_inicio` conta (eventos multi-dia não reaviso no fim); `user.activo` obrigatório (mesmo padrão das tarefas).
- *Assumpção:* relógio do servidor ≈ hora local de Portugal — desvio máximo de 1h no critério "já começou" não é crítico.

### 3. Refacto de testabilidade

Mover `app = create_app()` (linha 26 de módulo) para dentro de `if __name__ == '__main__':`. Hoje, qualquer import do script criaria a app com a **BD real** (`create_app()` default → `instance/pipe.db`, e o `create_app` chega a consultar a BD) — inaceitável num módulo que os testes vão importar. Nada importa o script, mudança mecânica e segura.

### 4. Testes (TDD) — `tests/test_pipe_tasks.py`

Padrão das fixtures de `tests/test_tarefas_listas_predefinidas.py` (`create_app('testing')` + asserção `memory`); `mock.patch('app.notifications.notification_service.send')` (o script importa a instância dentro da função, o patch na instância apanha a chamada); `hoje` é parâmetro das funções (testável sem patch de relógio; para "agora" criam-se eventos relativos a `datetime.now()`).

Cenários: vence-hoje 1× e dedupe no mesmo dia; atraso diário (ontem → amanhã notifica outra vez); concluída/sem prazo/futuro ignoradas; agrupamento por utilizador com as duas secções; "amanhã" no dia anterior; "hoje" no dia; sequência de 2 avisos sem duplicar; evento já iniciado ignorado; `dia_inteiro` incluído; `notificar=False` ignorado; evento antigo nunca casado; import do script não cria app.

### 5. Documentação (v1.5.8)

- `pipe_tasks.py` docstring: hora **07:00** + módulo Calendário.
- `Estado_Atual.md`: `:329` 08:00 → 07:00; tabela das scheduled tasks (linhas `tarefa_tarefas` e `tarefa_calendario`); pendência `:598` concluída; parágrafo **Versão v1.5.8**; título → v1.5.8.
- `CLAUDE.md` linha 8 → v1.5.8.

## Alternativas rejeitadas

- **Dois campos Date no `Evento`** (véspera/dia) — migração desnecessária; um campo com a semântica "última notificação" cobre a sequência.
- **Mensagens separadas por evento/tarefa** — spam; o padrão do projecto é agrupar por utilizador.
- **Aviso na criação de tarefa** — UX nova, fora de âmbito (decisão do utilizador).
- **Toggle de preferências** — fora de âmbito (decisão do utilizador); `notification_service` já filtra canais inactivos.

## Limitações conhecidas

- Tarefa criada com prazo de hoje após as 07:00 → primeiro aviso só no dia seguinte.
- Se o PA falhar um dia, perde-se o aviso daquele dia (ex.: "amanhã" perdido → o "hoje" do dia seguinte continua a funcionar).
- Eventos multi-dia: aviso só em relação a `data_inicio`.
