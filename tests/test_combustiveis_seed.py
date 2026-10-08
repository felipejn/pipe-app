"""Seed de concelhos predefinidos para o módulo Combustíveis."""
import os
import sys

import pytest
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.auth.models import User
from app.combustiveis.seed import semear_concelhos_predefinidos
from app.combustiveis.models import UtilizadorConcelho


@pytest.fixture
def app():
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


def test_cria_tres_concelhos(app):
    """Seed cria Braga, Vila Verde e Amares para utilizador sem concelhos."""
    with app.app_context():
        user = User(username='admin-teste', email='admin@exemplo.pt')
        user.password_hash = generate_password_hash('password-de-teste-123')
        db.session.add(user)
        db.session.commit()

        semear_concelhos_predefinidos(user.id)
        db.session.commit()

        concelhos = sorted(
            uc.concelho for uc in UtilizadorConcelho.query.filter_by(user_id=user.id).all()
        )
        assert concelhos == ['Amares', 'Braga', 'Vila Verde']


def test_nao_duplica(app):
    """Segunda chamada não duplica concelhos."""
    with app.app_context():
        user = User(username='admin2', email='admin2@exemplo.pt')
        user.password_hash = generate_password_hash('password-de-teste-123')
        db.session.add(user)
        db.session.commit()

        semear_concelhos_predefinidos(user.id)
        semear_concelhos_predefinidos(user.id)
        db.session.commit()

        count = UtilizadorConcelho.query.filter_by(user_id=user.id).count()
        assert count == 3


def test_nao_altera_concelhos_existentes(app):
    """Utilizador com concelhos próprios não é alterado."""
    with app.app_context():
        user = User(username='admin3', email='admin3@exemplo.pt')
        user.password_hash = generate_password_hash('password-de-teste-123')
        db.session.add(user)
        db.session.commit()

        db.session.add(UtilizadorConcelho(user_id=user.id, concelho='Porto'))
        db.session.commit()

        semear_concelhos_predefinidos(user.id)
        db.session.commit()

        concelhos = {
            uc.concelho for uc in UtilizadorConcelho.query.filter_by(user_id=user.id).all()
        }
        assert concelhos == {'Porto'}