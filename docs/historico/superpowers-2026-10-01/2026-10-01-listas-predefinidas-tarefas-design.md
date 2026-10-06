# Listas predefinidas no módulo de Tarefas — Design

**Data:** 2026-10-01
**Estado:** Aprovado pelo utilizador

## Contexto

O módulo de Tarefas (`/tarefas/`) arranca sem nenhuma lista para cada utilizador
novo — é preciso criar a primeira lista manualmente antes de poder adicionar
tarefas (o input de adição rápida só aparece numa lista concreta). O utilizador
quer que contas novas já nasçam com listas predefinidas, sem que o deploy toque
nas listas dos utilizadores já existentes.

## Decisões do utilizador

1. **Quando semear:** *apenas no registo de contas novas* (`registo_com_convite`).
   Utilizadores existentes no deploy ficam intocados — nada é apagado, nada é
   criado.
2. **Vista inicial:** manter **"Todas"** como vista por defeito do módulo.
   "Pessoal" é apenas a primeira lista da sidebar.
3. **Composição:** 4 listas — Pessoal 📌, Casa 🏠, Trabalho 💼, Compras 🛒.

## Abordagem escolhida

**Função helper no módulo `tarefas`, chamada da rota de registo** (Abordagem A).

Alternativa rejeitada: event listener `after_insert` no modelo `User` — magia
implícita e quebra silenciosa de testes que criam `User(...)` directamente
(ex.: `tests/test_assistente_combustiveis.py`).

Justificação do import cruzado `auth` → `tarefas`: já existe precedente — o
módulo `assistente` importa `Lista` de `app.tarefas.models`.

## Especificação

### 1. Constante `LISTAS_PREDEFINIDAS`

Nova função `semear_listas_predefinidas(user_id)` no módulo `app/tarefas`
(ficheiro `seed.py`), com a constante:

```python
LISTAS_PREDEFINIDAS = (
    ('Pessoal', '📌'),
    ('Casa',     '🏠'),
    ('Trabalho', '💼'),
    ('Compras',  '🛒'),
)
```

- `ordem` = índice (0–3), porque o index ordena por `Lista.ordem, Lista.data_criacao`.
- Ícones de um emoji cabem em `icone = db.Column(db.String(8))`.

### 2. Função idempotente

```python
def semear_listas_predefinidas(user_id):
    """Cria as listas predefinidas se o utilizador ainda não tiver nenhuma."""
```

- Guard defensivo: se o utilizador já tiver **alguma** lista, devolve sem fazer
  nada. **Nunca apaga, nunca duplica.**
- Cria as 4 listas com `user_id`, `nome`, `icone` e `ordem` da constante.
- Não faz `commit` — deixa a sessão pendente para o caller (commit único).

### 3. Integração em `registo_com_convite` (`app/auth/routes.py`)

```python
db.session.add(user)
db.session.flush()                      # obtém user.id
semear_listas_predefinidas(user.id)
# ... marcar convite usado ...
db.session.commit()                     # um único commit — tudo ou nada
```

### 4. Frontend — sem alterações

- Vista inicial continua "Todas".
- "Pessoal" aparece como primeira lista da sidebar (por `ordem=0`).

### 5. Fallback do assistente — sem alterações

`_obter_ou_criar_lista` cria `'Geral'` só quando o utilizador não tem nenhuma
lista; com o seed, esse caso só ocorre em contas antigas. YAGNI.

## Testes (TDD — escritos primeiro)

Novo ficheiro `tests/test_tarefas_listas_predefinidas.py`:

1. **Registo via convite cria as 4 listas** — nomes, ícones e ordem correctos,
   todas com o `user_id` do novo utilizador.
2. **Utilizador que já tem listas não é alterado** — chamar a função a um
   utilizador com listas próprias não duplica nem apaga nada.
3. **Função a utilizador sem listas** cria exactamente 4 listas (idempotência
   básica: segunda chamada não duplica).

Regras do repo: app com `create_app('testing')` (SQLite em memória), nunca a BD
real; comentários e mensagens em PT-PT.

## Documentação

- Actualizar `Estado_Atual.md` → v1.5.7.
- Actualizar a linha de versão em `CLAUDE.md`.

## Fora de âmbito

- Dar listas aos utilizadores existentes (seria um script one-shot à parte,
  se algum dia for pedido).
- Alterar a vista inicial para uma lista concreta.
- Alterar o fallback `'Geral'` do assistente.
