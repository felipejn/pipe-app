"""Listas predefinidas para contas novas.

Semeadas APENAS no registo (`auth.routes.registo_com_convite`) — nunca em
utilizadores já existentes. A função é idempotente: só cria as listas se o
utilizador ainda não tiver nenhuma, pelo que nunca apaga nem duplica
listas existentes (segurança para deploys).

Spec: docs/historico/superpowers-2026-10-01/2026-10-01-listas-predefinidas-tarefas-design.md
"""
from app import db
from app.tarefas.models import Lista

# (nome, icone) — a ordem na tupla é a ordem na sidebar (Lista.ordem = índice)
LISTAS_PREDEFINIDAS = (
    ('Pessoal', '📌'),
    ('Casa', '🏠'),
    ('Trabalho', '💼'),
    ('Compras', '🛒'),
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