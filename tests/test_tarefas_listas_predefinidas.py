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
from app.tarefas.seed import semear_listas_predefinidas


# (nome, icone, ordem) esperados, pela ordem da constante do seed
ESPERADAS = [
    ('Pessoal', '📌', 0),
    ('Casa', '🏠', 1),
    ('Trabalho', '💼', 2),
    ('Compras', '🛒', 3),
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


def _criar_convite(app, email):
    """Cria um convite válido (por um admin) e devolve o token."""
    with app.app_context():
        admin = User(username='admin-teste', email='admin@exemplo.pt')
        admin.password_hash = generate_password_hash('password-de-teste-123')
        admin.is_admin = True
        db.session.add(admin)
        db.session.flush()
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

def test_registo_cria_listas_predefinidas(app, client):
    """POST /auth/registo/<token> cria o utilizador com as 4 listas na ordem certa."""
    token = _criar_convite(app, 'novo@exemplo.pt')
    client.post(f'/auth/registo/{token}', data={
        'username': 'novo-utilizador',
        'email': 'novo@exemplo.pt',
        'password': 'password-de-teste-123',
        'password2': 'password-de-teste-123',
    }, follow_redirects=True)

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

        antes = [(l.nome, l.icone, l.ordem)
                 for l in Lista.query.filter_by(user_id=user.id).all()]
        semear_listas_predefinidas(user.id)
        db.session.commit()
        depois = [(l.nome, l.icone, l.ordem)
                  for l in Lista.query.filter_by(user_id=user.id).all()]
        assert depois == antes
        assert [l.nome for l in Lista.query.filter_by(user_id=user.id).all()] == ['Minha lista']


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
