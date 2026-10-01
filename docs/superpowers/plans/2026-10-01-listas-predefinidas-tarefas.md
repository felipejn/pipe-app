# Listas Predefinidas nas Tarefas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Contas novas nascem com 4 listas de tarefas predefinidas (Pessoal 📌, Casa 🏠, Trabalho 💼, Compras 🛒) sem tocar nas listas dos utilizadores já existentes no deploy.

**Architecture:** Função idempotente `semear_listas_predefinidas(user_id)` num novo módulo `app/tarefas/seed.py`, chamada pela rota `registo_com_convite` (`app/auth/routes.py`) logo após o `flush()` do utilizador, dentro do mesmo commit. Sem alterações de frontend — a vista inicial continua "Todas".

**Tech Stack:** Flask 3.0, SQLAlchemy (Flask-SQLAlchemy), pytest com `create_app('testing')` (SQLite em memória).

**Spec:** `docs/superpowers/specs/2026-10-01-listas-predefinidas-tarefas-design.md`

**Commits:** o utilizador pediu **um único commit no final**, depois de actualizada a documentação, seguido de `git push`. Não fazer commits por tarefa.

## Amendamentos pós-revisão (executado)

Os reviews obrigatórios alteraram o texto original dos Tasks 1 e 2; o ficheiro final é o válido:
- **Task 1 (testes):** removido o fixture `admin_client` (fazia o POST de registo sair autenticado — Critical C1); `_criar_convite(app, email)` cria admin+convite directamente no app context; snapshot completo `(nome, icone, ordem)` antes/depois no teste de não-alteração (I1); emojis literais em `ESPERADAS` (M2); sem `LISTAS_PREDEFINIDAS` importado (M1); sem `assert status_code` (M3); sem binding `r =` morto.
- **Task 2 (seed):** emojis literais na constante (consistência com `models.py`/`ferramentas.py`).
- **Task 5 (docs):** PT-PT ("chamada por", "condição de guarda explícita", "ponta a ponta"), frase do fallback corrigida e árvore do projecto actualizada (`seed.py`, `test_tarefas_listas_predefinidas.py`).

---

### Task 0: Verificação prévia

**Files:** nenhum

- [x] **Step 1: Confirmar árvore de trabalho e ramo**

Run (from `C:\Users\User\desktop\coding\pipe-app`):
```powershell
git status --porcelain; git branch --show-current
```
Expected: ramo `main`. Se houver ficheiros alterados não relacionados com esta tarefa, **parar** e perguntar ao utilizador antes de continuar.

---

### Task 1: Escrever os testes falhados

**Files:**
- Create: `C:\Users\User\desktop\coding\pipe-app\tests\test_tarefas_listas_predefinidas.py`

- [x] **Step 1: Criar o ficheiro de testes com o conteúdo completo seguinte**

```python
"""Listas predefinidas criadas no registo de contas novas.

O módulo de Tarefas arrancava vazio: o utilizador novo tinha de criar a
primeira lista à mão antes de poder adicionar tarefas (o input de adição
rápida só aparece numa lista concreta). Decisão do utilizador (spec em
docs/superpowers/specs/2026-10-01-listas-predefinidas-tarefas-design.md):
semear 4 listas APENAS no registo de contas novas — nunca tocar nas listas
de contas já existentes (deploy), nunca apagar nem duplicar.
"""
import os
import sys
from datetime import datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.auth.models import Convite, User
from app.tarefas.models import Lista
from app.tarefas.seed import LISTAS_PREDEFINIDAS, semear_listas_predefinidas


# (nome, icone, ordem) esperados, pela ordem da constante do seed
ESPERADAS = [
    ('Pessoal', '\U0001F4CC', 0),
    ('Casa', '\U0001F3E0', 1),
    ('Trabalho', '\U0001F4BC', 2),
    ('Compras', '\U0001F6D2', 3),
]


# ═════════ FIXTURES ═════════

@pytest.fixture
def app():
    """App de teste com SQLite in-memory (nunca toca em instance/pipe.db)."""
    app = create_app('testing')
    with app.app_context():
        uri = str(db.engine.url)
        assert 'memory' in uri, (
            f'ABORTADO: os testes estão a apontar para a BD real ({uri}).'
        )
        db.create_all()
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """Cliente com sessão de administrador (CSRF desligado no TestingConfig)."""
    with client.application.app_context():
        user = User(username='admin-teste', email='admin@exemplo.pt')
        user.password_hash = generate_password_hash('password-de-teste-123')
        user.is_admin = True
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    with client.session_transaction() as sess:
        sess['_user_id'] = user_id
    return client


def _criar_convite(client, email):
    """Cria um convite válido e devolve o token."""
    with client.application.app_context():
        admin = User.query.filter_by(username='admin-teste').first()
        convite = Convite(
            token=f'token-{email.replace("@", "-").replace(".", "-")}',
            email=email,
            criado_por=admin.id,
            expira_em=datetime.utcnow() + timedelta(days=7),
        )
        db.session.add(convite)
        db.session.commit()
        return convite.token


# ═════════ TESTES ═════════

def test_registo_cria_listas_predefinidas(client, admin_client):
    """POST /auth/registo/<token> cria o utilizador com as 4 listas na ordem certa."""
    token = _criar_convite(admin_client, 'novo@exemplo.pt')
    r = client.post(f'/auth/registo/{token}', data={
        'username': 'novo-utilizador',
        'email': 'novo@exemplo.pt',
        'password': 'password-de-teste-123',
        'password2': 'password-de-teste-123',
    }, follow_redirects=True)
    assert r.status_code == 200

    with client.application.app_context():
        user = User.query.filter_by(username='novo-utilizador').first()
        assert user is not None, 'registo não criou o utilizador'
        listas = Lista.query.filter_by(user_id=user.id).order_by(Lista.ordem).all()
        assert [(l.nome, l.icone, l.ordem) for l in listas] == ESPERADAS


def test_nao_altera_listas_existentes(app):
    """Utilizador que já tem listas próprias: o seed não duplica nem apaga."""
    with app.app_context():
        user = User(username='antigo', email='antigo@exemplo.pt')
        user.password_hash = generate_password_hash('password-de-teste-123')
        db.session.add(user)
        db.session.flush()
        db.session.add(Lista(nome='Minha lista', icone='⭐', user_id=user.id, ordem=0))
        db.session.commit()

        semear_listas_predefinidas(user.id)
        db.session.commit()

        listas = Lista.query.filter_by(user_id=user.id).all()
        assert [l.nome for l in listas] == ['Minha lista']


def test_segunda_chamada_nao_duplica(app):
    """Idempotência: chamar duas vezes cria exactamente 4 listas."""
    with app.app_context():
        user = User(username='novo2', email='novo2@exemplo.pt')
        user.password_hash = generate_password_hash('password-de-teste-123')
        db.session.add(user)
        db.session.commit()

        semear_listas_predefinidas(user.id)
        semear_listas_predefinidas(user.id)
        db.session.commit()

        listas = Lista.query.filter_by(user_id=user.id).order_by(Lista.ordem).all()
        assert [(l.nome, l.icone, l.ordem) for l in listas] == ESPERADAS
```

- [x] **Step 2: Correr os testes para confirmar que falham**

Run (from `C:\Users\User\desktop\coding\pipe-app`):
```powershell
& ".venv\Scripts\python.exe" -m pytest tests\test_tarefas_listas_predefinidas.py -v
```
Expected: FAIL na colecção com `ModuleNotFoundError: No module named 'app.tarefas.seed'` (o módulo de seed ainda não existe). Anotar a falha observada antes de avançar.

---

### Task 2: Implementar o módulo de seed

**Files:**
- Create: `C:\Users\User\desktop\coding\pipe-app\app\tarefas\seed.py`

- [x] **Step 1: Criar `app/tarefas/seed.py`**

```python
"""Listas predefinidas para contas novas.

Semeadas APENAS no registo (`auth.routes.registo_com_convite`) — nunca em
utilizadores já existentes. A função é idempotente: só cria as listas se o
utilizador ainda não tiver nenhuma, pelo que nunca apaga nem duplica
listas existentes (segurança para deploys).

Spec: docs/superpowers/specs/2026-10-01-listas-predefinidas-tarefas-design.md
"""
from app import db
from app.tarefas.models import Lista

# (nome, icone) — a ordem na tupla é a ordem na sidebar (Lista.ordem = índice)
LISTAS_PREDEFINIDAS = (
    ('Pessoal', '\U0001F4CC'),   # 📌
    ('Casa', '\U0001F3E0'),       # 🏠
    ('Trabalho', '\U0001F4BC'),   # 💼
    ('Compras', '\U0001F6D2'),    # 🛒
)


def semear_listas_predefinidas(user_id):
    """Cria as listas predefinidas se o utilizador ainda não tiver nenhuma.

    Nunca apaga nem duplica. Não faz commit — deixa a sessão pendente para
    o caller (commit único, tudo ou nada).
    """
    if Lista.query.filter_by(user_id=user_id).first():
        return
    for ordem, (nome, icone) in enumerate(LISTAS_PREDEFINIDAS):
        db.session.add(Lista(nome=nome, icone=icone, ordem=ordem, user_id=user_id))
```

- [x] **Step 2: Correr os testes — os dois testes unitários devem passar**

Run:
```powershell
& ".venv\Scripts\python.exe" -m pytest tests\test_tarefas_listas_predefinidas.py -v
```
Expected: `test_nao_altera_listas_existentes` e `test_segunda_chamada_nao_duplica` PASS; `test_registo_cria_listas_predefinidas` FAIL (a rota de registo ainda não chama o seed — falha com 0 listas criadas).

---

### Task 3: Ligar o seed à rota de registo

**Files:**
- Modify: `C:\Users\User\desktop\coding\pipe-app\app\auth\routes.py` (import no topo + função `registo_com_convite`, linha ~268)

- [x] **Step 1: Adicionar o import**

Após a linha `from app.extensions import limiter` (linha 20) em `app/auth/routes.py`:

```python
from app.tarefas.seed import semear_listas_predefinidas
```

- [x] **Step 2: Chamar o seed dentro de `registo_com_convite`**

Substituir o bloco (linhas ~268-274):

```python
        user = User(username=form.username.data, email=form.email.data.lower().strip())
        user.set_password(form.password.data)
        db.session.add(user)

        convite.usado = True
        convite.usado_em = datetime.utcnow()
        db.session.commit()
```

por:

```python
        user = User(username=form.username.data, email=form.email.data.lower().strip())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # obtém user.id para semear as listas predefinidas
        semear_listas_predefinidas(user.id)

        convite.usado = True
        convite.usado_em = datetime.utcnow()
        db.session.commit()
```

- [x] **Step 3: Correr os 3 testes do módulo**

Run:
```powershell
& ".venv\Scripts\python.exe" -m pytest tests\test_tarefas_listas_predefinidas.py -v
```
Expected: 3 passed.

---

### Task 4: Suíte completa de regressão

**Files:** nenhum (validação)

- [x] **Step 1: Correr todos os testes**

Run (from `C:\Users\User\desktop\coding\pipe-app`):
```powershell
& ".venv\Scripts\python.exe" -m pytest tests\ -q
```
Expected: todos PASS. Se algum teste pré-existente falhar, investigar antes de avançar (a mudança toca em `registo_com_convite` — verificar se algum teste exercita o registo).

---

### Task 5: Documentação (v1.5.7)

**Files:**
- Modify: `C:\Users\User\desktop\coding\pipe-app\Estado_Atual.md`
- Modify: `C:\Users\User\desktop\coding\pipe-app\CLAUDE.md`

- [x] **Step 1: `Estado_Atual.md` — título (linha 1)**

De:
```markdown
# PIPE — Estado Actual do Projecto — v1.5.6
```
Para:
```markdown
# PIPE — Estado Actual do Projecto — v1.5.7
```

- [x] **Step 2: `Estado_Atual.md` — secção Tarefas (depois da linha 208, «- **Mobile:** …»)**

Inserir novo item:
```markdown
- **Listas predefinidas no registo (v1.5.7):** contas novas nascem com 4 listas — Pessoal 📌 (ordem 0), Casa 🏠, Trabalho 💼, Compras 🛒 — criadas por `app/tarefas/seed.py::semear_listas_predefinidas(user_id)` chamada de `registo_com_convite` no mesmo commit. Função idempotente: só semeia se o utilizador não tiver nenhuma lista (nunca apaga nem duplica) — o deploy não toca nas listas das contas existentes. Vista inicial mantém-se "Todas".
```

- [x] **Step 3: `Estado_Atual.md` — «Ponto onde estamos» (linha 546)**

Inserir novo parágrafo de versão imediatamente **depois** do cabeçalho `## Ponto onde estamos` (antes do parágrafo `**Versão v1.5.2**`):
```markdown
**Versão v1.5.7** — listas predefinidas no módulo de Tarefas para contas novas. Novo `app/tarefas/seed.py` com a constante `LISTAS_PREDEFINIDAS` (Pessoal 📌, Casa 🏠, Trabalho 💼, Compras 🛒 — `ordem` 0–3, ícones de um emoji no `String(8)`) e `semear_listas_predefinidas(user_id)`, chamada por `registo_com_convite` (`app/auth/routes.py`) logo a seguir ao `flush()` do utilizador e antes do `commit` — um único commit, tudo ou nada. A função é idempotente com guard explícito (só semeia se o utilizador não tiver **nenhuma** lista): nunca apaga nem duplica, pelo que o deploy não toca nas listas das contas já existentes — decisão do utilizador: semear **apenas no registo**. Frontend sem alterações: vista inicial continua «Todas» («Pessoal» é só a primeira lista da sidebar) e o fallback `Geral` do assistente (`_obter_ou_criar_lista`) ficou intacto — só dispara em contas antigas sem listas. Testes em `tests/test_tarefas_listas_predefinidas.py` (registo ponta-a-ponta via convite + guarda de não-alteração de listas existentes + idempotência). Spec: `docs/superpowers/specs/2026-10-01-listas-predefinidas-tarefas-design.md`.
```

- [x] **Step 4: `CLAUDE.md` — linha de versão (linha 8)**

De:
```markdown
- **Versão actual:** v1.5.6 (Calendário inicia na vista Mensal, modo claro do Calendário ao estilo Google Calendar, tarefas concluídas ocultas por defeito) — detalhe em `Estado_Atual.md`
```
Para:
```markdown
- **Versão actual:** v1.5.7 (contas novas nascem com 4 listas de tarefas predefinidas — Pessoal, Casa, Trabalho, Compras) — detalhe em `Estado_Atual.md`
```

---

### Task 6: Commit e push (pedido do utilizador — no final)

**Files:** todos os anteriores

- [x] **Step 1: Rever o que vai ser commitado**

Run (from `C:\Users\User\desktop\coding\pipe-app`):
```powershell
git status --porcelain; git diff --stat
```
Expected: apenas os ficheiros desta tarefa — `app/tarefas/seed.py` (novo), `app/auth/routes.py`, `tests/test_tarefas_listas_predefinidas.py` (novo), `Estado_Atual.md`, `CLAUDE.md`, `docs/superpowers/specs/2026-10-01-listas-predefinidas-tarefas-design.md` (novo), `docs/superpowers/plans/2026-10-01-listas-predefinidas-tarefas.md` (novo). Se aparecerem outros ficheiros alterados, **parar** e perguntar ao utilizador.

- [x] **Step 2: Commit**

```powershell
git add app/tarefas/seed.py app/auth/routes.py tests/test_tarefas_listas_predefinidas.py Estado_Atual.md CLAUDE.md docs/superpowers/
git commit -m "feat(tarefas): listas predefinidas no registo de contas novas"
```

- [x] **Step 3: Push**

```powershell
git push
```
Expected: push para `origin/main` sem erros. Se o push falhar por divergência, correr `git pull --rebase` e repetir.



