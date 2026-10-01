# Plano — Notificações: tarefas (vence hoje + atraso) e calendário (dia anterior + dia)

**Data:** 2026-10-01 · **Versão resultante:** v1.5.8 · **Spec:** `docs/superpowers/specs/2026-10-01-notificacoes-tarefas-calendario-design.md`

**Commits:** um único commit no final, depois de actualizada a documentação, seguido de `git push`. Não fazer commits por tarefa.

## Amendamento pós-RED (executado)

Task 2 resultou em **10 failed / 3 passed** (o plano previa 12/1): `test_tarefas_avisa_diariamente_em_atraso` e `test_tarefas_ignora_concluida_sem_prazo_e_futura` passam já contra o código antigo — **protegem comportamento pré-existente** (regressão), não invalidam o RED. Os 10 falhantes cobrem 100% do comportamento novo (3 tarefas novas + 7 calendário). RED válido.

**Fora de âmbito (decisão do utilizador):** toggle de preferências para eventos/tarefas; aviso na criação de tarefa com prazo de hoje.

**TDD:** os testes (Task 2) escrevem-se ANTES da implementação (Task 3 e 4) e têm de falhar primeiro.

---

### Task 0: Verificação prévia

**Files:** nenhum

- [x] **Step 1:** árvore limpa, `main`, HEAD `8b0014b`, upstream OK.
- [x] **Step 2:** suíte verde: `122 passed`.
- [ ] **Step 3:** confirmar `python-dotenv` no `requirements.txt` (o script importa `load_dotenv`).

### Task 1: Refacto — `app = create_app()` para dentro de `__main__`

**Files:** `scripts/pipe_tasks.py`

Hoje `app = create_app()` está no âmbulo de módulo (linha 26); importar o script cria a app com a **BD real** (`Config.SQLALCHEMY_DATABASE_URI` → `instance/pipe.db`) — inaceitável para os testes que o vão importar. Nada importa o script (só comentários), mudança mecânica.

### Task 2: Testes (RED) — `tests/test_pipe_tasks.py`

**Files:** novo `tests/test_pipe_tasks.py`

- [ ] **Step 1:** criar o ficheiro com os 3 blocos de código seguintes (início + tarefas + calendário).
- [ ] **Step 2:** correr `& '.\.venv\Scripts\python.exe' -m pytest tests\test_pipe_tasks.py -v` → **esperado: TODOS FALHAM** (`tarefa_calendario` ainda não existe → `ImportError`; `tarefa_tarefas` com comportamento antigo). Se algum passar, PARAR e reportar.

**Bloco A (início do ficheiro):**

```python
"""Notificações diárias do pipe_tasks: tarefas e calendário.

Tarefas: avisam no dia do prazo («Vencem hoje») e depois em todos os dias de
atraso até concluir, 1× por dia (dedupe por `notificada_em`).
Calendário: avisam no dia anterior («Amanhã») e no dia («Hoje»); o campo único
`Evento.notificado_em` cobre os dois avisos sem migração de BD.

Spec: docs/superpowers/specs/2026-10-01-notificacoes-tarefas-calendario-design.md
"""
import os
import sys
from datetime import date, datetime, timedelta
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))

from app import create_app, db
from app.auth.models import User
from app.calendario.models import Evento
from app.tarefas.models import Lista, Tarefa

import pipe_tasks


@pytest.fixture
def app():
    """App de teste com SQLite in-memory (nunca toca em instance/pipe.db)."""
    app = create_app('testing')
    with app.app_context():
        uri = str(db.engine.url)
        assert 'memory' in uri, f'ABORTADO: os testes apontam para a BD real ({uri}).'
        db.create_all()
        yield app
        db.session.remove()


@pytest.fixture
def enviar():
    """Captura as chamadas a notification_service.send (nada é enviado a sério)."""
    with mock.patch('app.notifications.notification_service.send') as m:
        yield m


def _criar_user(username):
    user = User(username=username, email=f'{username}@exemplo.pt')
    user.set_password('password-de-teste-123')
    user.activo = True
    db.session.add(user)
    db.session.flush()
    lista = Lista(nome='Geral', user_id=user.id)
    db.session.add(lista)
    db.session.flush()
    return user, lista


def _criar_tarefa(lista, user, texto, data_limite, concluida=False, notificada_em=None):
    t = Tarefa(texto=texto, concluida=concluida, data_limite=data_limite,
               notificada_em=notificada_em, lista_id=lista.id, user_id=user.id)
    db.session.add(t)
    db.session.commit()
    return t


def _criar_evento(user, data_inicio, horas=1, dia_inteiro=False, notificar=True,
                  titulo='Evento', notificado_em=None, localizacao=None):
    e = Evento(user_id=user.id, titulo=titulo, localizacao=localizacao,
               data_inicio=data_inicio, data_fim=data_inicio + timedelta(hours=horas),
               dia_inteiro=dia_inteiro, notificar=notificar,
               notificado_em=notificado_em, cor='tomate')
    db.session.add(e)
    db.session.commit()
    return e


def _chamadas(enviar):
    """Dict {username: kwargs} das chamadas a send()."""
    return {c.kwargs['user'].username: c.kwargs for c in enviar.call_args_list}


def test_import_do_script_nao_cria_app():
    """Importar pipe_tasks não pode criar a app (BD real) — pré-requisito dos testes."""
    assert not hasattr(pipe_tasks, 'app'), (
        'pipe_tasks tem `app` no âmbulo de módulo — mover create_app() para __main__.')

```

**Bloco B (testes de tarefas — acrescentar ao mesmo ficheiro):**

```python
def test_tarefas_avisa_no_dia_do_prazo(app, enviar):
    hoje = date.today()
    user, lista = _criar_user('util-tarefas')
    t = _criar_tarefa(lista, user, 'Pagar factura', hoje)

    pipe_tasks.tarefa_tarefas(hoje)

    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert kw['type'] == 'tarefa_lembrete'
    assert 'hoje' in kw['subject'].lower()
    assert 'atraso' not in kw['subject'].lower()
    assert 'Pagar factura' in kw['body']
    db.session.refresh(t)
    assert t.notificada_em == hoje


def test_tarefas_nao_repete_no_mesmo_dia(app, enviar):
    hoje = date.today()
    user, lista = _criar_user('util-dedupe')
    _criar_tarefa(lista, user, 'Tarefa única', hoje)

    pipe_tasks.tarefa_tarefas(hoje)
    pipe_tasks.tarefa_tarefas(hoje)   # segunda corrida no mesmo dia

    assert enviar.call_count == 1


def test_tarefas_avisa_diariamente_em_atraso(app, enviar):
    hoje = date.today()
    user, lista = _criar_user('util-atraso')
    _criar_tarefa(lista, user, 'Relatório atrasado', hoje - timedelta(days=3))

    pipe_tasks.tarefa_tarefas(hoje)
    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert 'atraso' in kw['subject'].lower()
    assert '3 dia' in kw['body']

    pipe_tasks.tarefa_tarefas(hoje + timedelta(days=1))   # dia seguinte
    assert enviar.call_count == 2


def test_tarefas_ignora_concluida_sem_prazo_e_futura(app, enviar):
    hoje = date.today()
    user, lista = _criar_user('util-ignora')
    _criar_tarefa(lista, user, 'Já feita', hoje, concluida=True)
    _criar_tarefa(lista, user, 'Sem prazo', None)
    _criar_tarefa(lista, user, 'Para amanhã', hoje + timedelta(days=1))

    pipe_tasks.tarefa_tarefas(hoje)

    assert enviar.call_count == 0


def test_tarefas_agrupa_utilizador_com_duas_secções(app, enviar):
    hoje = date.today()
    user_a, lista_a = _criar_user('util-misto')
    user_b, lista_b = _criar_user('util-simples')
    _criar_tarefa(lista_a, user_a, 'Hoje A', hoje)
    _criar_tarefa(lista_a, user_a, 'Ontem A', hoje - timedelta(days=1))
    _criar_tarefa(lista_b, user_b, 'Hoje B', hoje)

    pipe_tasks.tarefa_tarefas(hoje)

    assert enviar.call_count == 2
    por_user = _chamadas(enviar)
    kw_a = por_user['util-misto']
    assert 'Vencem hoje' in kw_a['body'] and 'Em atraso' in kw_a['body']
    assert kw_a['data'] == {'total_hoje': 1, 'total_atraso': 1}
    kw_b = por_user['util-simples']
    assert 'Vencem hoje' in kw_b['body'] and 'Em atraso' not in kw_b['body']

```

**Bloco C (testes de calendário — acrescentar ao mesmo ficheiro):**

```python
def test_calendario_avisa_dia_anterior(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-cal')
    amanha10 = (datetime.now() + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0)
    e = _criar_evento(user, amanha10, titulo='Reunião', localizacao='Escritório')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert kw['type'] == 'evento_lembrete'
    assert 'amanhã' in kw['subject'].lower()
    assert 'Reunião' in kw['body'] and 'Escritório' in kw['body']
    db.session.refresh(e)
    assert e.notificado_em == hoje


def test_calendario_avisa_no_dia(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-cal-hoje')
    e = _criar_evento(user, datetime.now() + timedelta(hours=2), titulo='Consulta')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert 'hoje' in kw['subject'].lower()
    assert 'Consulta' in kw['body']
    db.session.refresh(e)
    assert e.notificado_em == hoje


def test_calendario_sequencia_dois_avisos_sem_duplicar(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-sequencia')
    amanha10 = (datetime.now() + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0)
    e = _criar_evento(user, amanha10, titulo='Concerto')

    pipe_tasks.tarefa_calendario(hoje)                      # véspera → «Amanhã»
    pipe_tasks.tarefa_calendario(hoje + timedelta(days=1))  # dia do evento → «Hoje»
    pipe_tasks.tarefa_calendario(hoje + timedelta(days=2))  # depois → nada

    assert enviar.call_count == 2
    assert 'amanhã' in enviar.call_args_list[0].kwargs['subject'].lower()
    assert 'hoje' in enviar.call_args_list[1].kwargs['subject'].lower()
    db.session.refresh(e)
    assert e.notificado_em == hoje + timedelta(days=1)


def test_calendario_ignora_evento_ja_iniciado(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-iniciado')
    passado = datetime.now().replace(hour=0, minute=5, second=0, microsecond=0)
    _criar_evento(user, passado, titulo='Já passou')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 0


def test_calendario_inclui_dia_inteiro(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-dia-inteiro')
    meia_noite = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    _criar_evento(user, meia_noite, dia_inteiro=True, titulo='Aniversário')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert 'hoje' in kw['subject'].lower()
    assert 'dia inteiro' in kw['body']


def test_calendario_respeita_toggle_notificar(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-silencio')
    amanha10 = (datetime.now() + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0)
    _criar_evento(user, amanha10, notificar=False, titulo='Sigiloso')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 0


def test_calendario_ignora_eventos_antigos(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-antigo')
    antigo = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) \
        - timedelta(days=7)
    _criar_evento(user, antigo, titulo='Evento velho')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 0

```

### Task 3: `tarefa_tarefas` — avisar no dia do prazo (GREEN)

**Files:** `scripts/pipe_tasks.py`

- [ ] **Step 1:** substituir INTEGRALMENTE a função `tarefa_tarefas` (linhas ~115-173, desde `def tarefa_tarefas(hoje):` até à linha `print(f'  [Tarefas] {notificados} tarefa(s)...')`) pelo bloco:

```python
def tarefa_tarefas(hoje):
    print(f'  [Tarefas] A verificar prazos...')

    from app.tarefas.models import Tarefa
    from app.auth.models import User
    from app.notifications import notification_service

    # Tarefas com prazo para HOJE ou já em atraso, não notificadas ainda hoje
    candidatas = Tarefa.query.filter(
        Tarefa.concluida == False,           # noqa: E712
        Tarefa.data_limite != None,          # noqa: E711
        Tarefa.data_limite <= hoje,          # vence hoje OU prazo ultrapassado
        db.or_(
            Tarefa.notificada_em == None,    # nunca notificada   # noqa: E711
            Tarefa.notificada_em < hoje,     # última notificação foi antes de hoje
        ),
    ).all()

    if not candidatas:
        print(f'  [Tarefas] Sem tarefas para notificar hoje.')
        return

    # Agrupar por utilizador
    por_user = {}
    for t in candidatas:
        por_user.setdefault(t.user_id, []).append(t)

    notificados = 0
    for user_id, lista in por_user.items():
        user = User.query.get(user_id)
        if not user or not user.activo:
            continue

        hoje_lista  = [t for t in lista if t.data_limite == hoje]
        atraso_lista = [t for t in lista if t.data_limite < hoje]

        # Secções da mensagem (cada uma só aparece se tiver itens)
        partes = []
        if hoje_lista:
            itens = '\n'.join(
                f'• {t.texto} (limite: {t.data_limite.strftime("%d/%m/%Y")})'
                for t in hoje_lista
            )
            partes.append(f'⏰ Vencem hoje ({len(hoje_lista)}):\n{itens}')
        if atraso_lista:
            itens = '\n'.join(
                f'• {t.texto} (limite: {t.data_limite.strftime("%d/%m/%Y")}, '
                f'{(hoje - t.data_limite).days} dia(s) de atraso)'
                for t in atraso_lista
            )
            partes.append(f'⚠ Em atraso ({len(atraso_lista)}):\n{itens}')

        n_hoje, n_atraso = len(hoje_lista), len(atraso_lista)
        if n_hoje and n_atraso:
            subject = (f'⏰ {n_hoje} tarefa{"s" if n_hoje > 1 else ""} com prazo hoje '
                       f'e {n_atraso} em atraso no PIPE')
        elif n_hoje:
            subject = f'⏰ {n_hoje} tarefa{"s" if n_hoje > 1 else ""} com prazo hoje no PIPE'
        else:
            subject = f'⚠ {n_atraso} tarefa{"s" if n_atraso > 1 else ""} em atraso no PIPE'

        body = (
            f'Olá {user.username},\n\n'
            + '\n\n'.join(partes)
            + '\n\nAcede ao PIPE para concluir ou actualizar os prazos.'
        )

        res = notification_service.send(
            user=user, type='tarefa_lembrete',
            subject=subject, body=body,
            data={'total_hoje': n_hoje, 'total_atraso': n_atraso})
        print(f'  [Tarefas] {user.username}: hoje={n_hoje} atraso={n_atraso} '
              f'— telegram={res.get("telegram")}  email={res.get("email")}')

        # Marcar com a data de hoje — amanhã, se ainda faltar, volta a notificar
        for t in lista:
            t.notificada_em = hoje
        db.session.commit()
        notificados += len(lista)

    print(f'  [Tarefas] {notificados} tarefa(s) notificada(s) em {len(por_user)} utilizador(es).')
```

- [ ] **Step 2:** correr `& '.\.venv\Scripts\python.exe' -m pytest tests\test_pipe_tasks.py -v` → esperado: **todos os testes de TAREFAS passam** (5), `test_import_do_script_nao_cria_app` passa, e os de CALENDÁRIO falham (7 — `tarefa_calendario` ainda não existe).

### Task 4: `tarefa_calendario` — dia anterior + dia (GREEN)

**Files:** `scripts/pipe_tasks.py`

- [ ] **Step 1:** alterar o import do topo, linha 17: `from datetime date` → `from datetime import date, datetime, timedelta` (exactamente: `from datetime import date, datetime, timedelta`).
- [ ] **Step 2:** acrescentar a secção MÓDULO 4 DEPOIS da secção MÓDULO 3 (`tarefa_combustiveis`) e ANTES do separador `# ADICIONAR NOVOS MÓDULOS AQUI`:

```python
# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 4 — Calendário
# Lembretes de eventos: no dia ANTERIOR («Amanhã») e no PRÓPRIO DIA («Hoje»).
# O campo único notificado_em cobre os dois avisos: no dia D−1 grava D−1; no
# dia D (do evento), como notificado_em < D, volta a notificar e grava D.
# Eventos já iniciados à hora da task (não dia inteiro) são ignorados.
# ══════════════════════════════════════════════════════════════════════════════

def tarefa_calendario(hoje):
    print(f'  [Calendário] A verificar eventos...')

    from app.calendario.models import Evento
    from app.auth.models import User
    from app.notifications import notification_service

    amanha = hoje + timedelta(days=1)
    agora = datetime.now()

    eventos = Evento.query.filter(
        Evento.notificar == True,                      # noqa: E712
        db.or_(
            Evento.notificado_em == None,              # nunca notificado  # noqa: E711
            Evento.notificado_em < hoje,               # notificado antes de hoje
        ),
        db.or_(
            db.func.date(Evento.data_inicio) == amanha,        # → «Amanhã»
            db.and_(
                db.func.date(Evento.data_inicio) == hoje,      # → «Hoje»
                db.or_(
                    Evento.dia_inteiro == True,                # noqa: E712
                    Evento.data_inicio > agora,                # ainda não começou
                ),
            ),
        ),
    ).order_by(Evento.data_inicio).all()

    if not eventos:
        print(f'  [Calendário] Sem eventos para notificar.')
        return

    # Agrupar por utilizador
    por_user = {}
    for e in eventos:
        por_user.setdefault(e.user_id, []).append(e)

    def _linha(e):
        quando = 'dia inteiro' if e.dia_inteiro else f'às {e.data_inicio.strftime("%H:%M")}'
        local = f' — {e.localizacao}' if e.localizacao else ''
        return f'• {e.titulo} ({quando}){local}'

    notificados = 0
    for user_id, lista in por_user.items():
        user = User.query.get(user_id)
        if not user or not user.activo:
            continue

        amanha_lista = [e for e in lista if e.data_inicio.date() == amanha]
        hoje_lista = [e for e in lista if e.data_inicio.date() == hoje]

        partes = []
        if amanha_lista:
            itens = '\n'.join(_linha(e) for e in amanha_lista)
            partes.append(f'📅 Amanhã ({len(amanha_lista)}):\n{itens}')
        if hoje_lista:
            itens = '\n'.join(_linha(e) for e in hoje_lista)
            partes.append(f'📅 Hoje ({len(hoje_lista)}):\n{itens}')

        n_a, n_h = len(amanha_lista), len(hoje_lista)
        if n_a and n_h:
            subject = f'📅 {n_a} evento{"s" if n_a > 1 else ""} amanhã e {n_h} hoje no PIPE'
        elif n_a:
            subject = f'📅 {n_a} evento{"s" if n_a > 1 else ""} amanhã no PIPE'
        else:
            subject = f'📅 {n_h} evento{"s" if n_h > 1 else ""} hoje no PIPE'

        body = (
            f'Olá {user.username},\n\n'
            + '\n\n'.join(partes)
            + '\n\nAcede ao PIPE ao Calendário para ver os detalhes.'
        )

        res = notification_service.send(
            user=user, type='evento_lembrete',
            subject=subject, body=body,
            data={'total_amanha': n_a, 'total_hoje': n_h})
        print(f'  [Calendário] {user.username}: amanhã={n_a} hoje={n_h} '
              f'— telegram={res.get("telegram")}  email={res.get("email")}')

        # Um único campo cobre os dois avisos — amanhã passa a «hoje» e notifica
        for e in lista:
            e.notificado_em = hoje
        db.session.commit()
        notificados += len(lista)

    print(f'  [Calendário] {notificados} evento(s) notificado(s) em {len(por_user)} utilizador(es).')
```

- [ ] **Step 3:** registar em `TAREFAS` (linha ~204): `tarefa_combustiveis,` passa a ser seguido de `tarefa_calendario,`.
- [ ] **Step 4:** correr `& '.\.venv\Scripts\python.exe' -m pytest tests\test_pipe_tasks.py -v` → esperado: **13 passed**.
### Task 5: Suíte completa de regressão

**Files:** nenhum

- [ ] **Step 1:** correr `& '.\.venv\Scripts\python.exe' -m pytest tests\ -q` → esperado: **135 passed, 0 failed** (122 prévios + 13 novos).
- [ ] **Step 2:** se algo falhar, corrigir no módulo afectado (nunca nos testes, salvo erro demonstrado do teste).

### Task 6: Documentação (v1.5.8)

**Files:** `scripts/pipe_tasks.py` (docstring), `Estado_Atual.md`, `CLAUDE.md`

- [ ] **Step 1 — docstring do script:** substituir o bloco de linhas 6-12 por:

```
Configuração no PA:
  Comando: python /home/felipejn/pipe-app/scripts/pipe_tasks.py
  Hora:    07:00

Módulos activos:
  1. Euromilhões — verifica resultados às terças e sextas
  2. Tarefas     — avisa no dia do prazo e em atraso (diariamente até concluir)
  3. Combustíveis — actualiza preços às terças
  4. Calendário  — lembretes de eventos no dia anterior e no dia
```

- [ ] **Step 2 — Estado_Atual.md:**
  1. Linha 1: `v1.5.7` → `v1.5.8`.
  2. Linha 329: `(08:00)` → `(07:00)`.
  3. Linha da tabela `tarefa_tarefas` → `| \`tarefa_tarefas\` | Todos os dias | Notifica tarefas com prazo para hoje («Vencem hoje») e em atraso — 1×/dia, diariamente enquanto persistirem |`
  4. Linha da tabela `tarefa_calendario_hoje` → `| \`tarefa_calendario\` | Todos os dias | Lembretes de eventos: no dia anterior («Amanhã») e no dia («Hoje»); ignora eventos já iniciados e respeita o toggle \`notificar\` |`
  5. Em «**Pendências do Calendário:**», APAGAR o bullet `- \`tarefa_calendario_hoje()\` em \`pipe_tasks.py\` — notificação de eventos do dia seguinte às 08:00` (passa a estar feito).
  6. Em «## Ponto onde estamos», inserir NOVO parágrafo antes do **Versão v1.5.7** (texto exato):

**Versão v1.5.8** — notificações diárias alargadas. `tarefa_tarefas()` passa a avisar também **no dia do prazo** (`data_limite <= hoje`) e depois em todos os dias de atraso até concluir, numa única mensagem por utilizador com as secções «⏰ Vencem hoje» e «⚠ Em atraso» (`type='tarefa_lembrete'`). Nova `tarefa_calendario()` em `pipe_tasks.py` — lembretes de eventos **no dia anterior** («Amanhã») e **no dia** («Hoje»), agrupados por utilizador (`type='evento_lembrete'`), ignorando eventos já iniciados (excepto dia inteiro) e respeitando o toggle `notificar` — completa a pendência desde a v1.4.2 **sem migração de BD** (o campo único `Evento.notificado_em` cobre os dois avisos: véspera grava D−1, dia do evento grava D). Refacto: `app = create_app()` movido para dentro de `if __name__ == '__main__'` — importar o script já não cria a app com a BD real (pré-requisito dos testes). Hora real da scheduled task corrigida em todo lado: **07:00** (o docstring dizia 23:00 e o `Estado_Atual.md` 08:00). Testes: novo `tests/test_pipe_tasks.py` (13 testes, `notification_service.send` mockado). Fora de âmbito (decisão do utilizador): toggle de preferências para eventos/tarefas e aviso na criação de tarefa. Spec: `docs/superpowers/specs/2026-10-01-notificacoes-tarefas-calendario-design.md`.

- [ ] **Step 3 — CLAUDE.md linha 8:** substituir por:
  `- **Versão actual:** v1.5.8 (tarefas avisam no dia do prazo + atraso; Calendário avisa no dia anterior e no dia) — detalhe em \`Estado_Atual.md\``
- [ ] **Step 4:** verificar CRLF sem linhas mistas nos dois `.md` e reler as zonas editadas.

### Task 7: Revisão final + commit único + push

**Files:** todos

- [ ] **Step 1:** dispatch do reviewer final sobre TODA a implementação (spec compliance + qualidade + exactitude da documentação).
- [ ] **Step 2:** corrigir findings Críticos/Importantes; repetir revisão; repetir até veredito **READY TO MERGE**.
- [ ] **Step 3:** limpar artefactos (logs/testes temporários) — `git status --porcelain` só com os ficheiros previstos: `M CLAUDE.md, M Estado_Atual.md, M scripts/pipe_tasks.py`, `?? tests/test_pipe_tasks.py`, `?? docs/superpowers/` (spec+plano novos).
- [ ] **Step 4:** `git add` dos ficheiros previstos + `git commit -m "feat(notificacoes): tarefas avisam no dia do prazo e calendario no dia anterior e no dia (v1.5.8)"` + `git push`.
- [ ] **Step 5:** confirmar `git status` limpo e upstream sincronizado.




- [ ] **Step 1:** remover a linha `app = create_app()` e a linha em branco que a acompanha do âmbulo de módulo; acrescentar `app = create_app()` como PRIMEIRA linha dentro de `if __name__ == '__main__':` (antes de `hoje = date.today()`).
- [ ] **Step 2:** verificar: `& '.\.venv\Scripts\python.exe' -c "import sys; sys.path.insert(0, r'C:\Users\User\desktop\coding\pipe-app\scripts'); import pipe_tasks; assert not hasattr(pipe_tasks, 'app'); print('OK')"` → `OK`.
- [ ] **Step 3:** `git diff scripts/pipe_tasks.py` mostra apenas essa mudança.

