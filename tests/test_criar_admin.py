"""Testes para scripts/criar_admin.py."""
import os
import sys
from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.auth.models import User
from app.combustiveis.models import Posto, UtilizadorConcelho
from app.tarefas.models import Lista
from scripts import criar_admin


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


def _criar_admin(app, monkeypatch, username='admin-teste', email='admin@exemplo.pt', password='password'):
    inputs = iter([username, email, password])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    monkeypatch.setattr(criar_admin, 'create_app', lambda env: app)
    criar_admin.criar_admin()


def test_cria_admin_com_listas_e_concelhos(app, monkeypatch):
    """Criar admin -> tem as 4 listas predefinidas e os 3 concelhos."""
    _criar_admin(app, monkeypatch)

    with app.app_context():
        user = User.query.filter_by(username='admin-teste').first()
        assert user is not None
        assert user.is_admin is True

        listas = Lista.query.filter_by(user_id=user.id).order_by(Lista.ordem).all()
        assert [(l.nome, l.icone, l.ordem) for l in listas] == [
            ('Pessoal', '📌', 0),
            ('Casa', '🏠', 1),
            ('Trabalho', '💼', 2),
            ('Compras', '🛒', 3),
        ]

        concelhos = sorted(
            uc.concelho for uc in UtilizadorConcelho.query.filter_by(user_id=user.id).all()
        )
        assert concelhos == ['Amares', 'Braga', 'Vila Verde']


def test_segunda_criacao_nao_duplica(app, monkeypatch):
    """Correr duas vezes com mesmo username -> nao duplica utilizador, listas nem concelhos."""
    _criar_admin(app, monkeypatch)
    _criar_admin(app, monkeypatch, username='admin-teste')

    with app.app_context():
        assert User.query.filter_by(username='admin-teste').count() == 1

        user = User.query.filter_by(username='admin-teste').first()
        assert Lista.query.filter_by(user_id=user.id).count() == 4
        assert UtilizadorConcelho.query.filter_by(user_id=user.id).count() == 3


def test_utilizador_existente_com_concelhos_proprios_nao_altera(app, monkeypatch):
    """Seed nao sobrescreve concelhos que o utilizador ja configurou."""
    with app.app_context():
        user = User(username='admin-existing', email='admin-existing@exemplo.pt')
        user.password_hash = generate_password_hash('password')
        db.session.add(user)
        db.session.commit()

        db.session.add(UtilizadorConcelho(user_id=user.id, concelho='Porto'))
        db.session.commit()

    inputs = iter(['admin-existing', 'admin-existing@exemplo.pt', 'password'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    monkeypatch.setattr(criar_admin, 'create_app', lambda env: app)

    with patch.object(criar_admin.services, 'atualizar_precos_se_necessario', return_value={
        'executado': True, 'sucesso': True, 'precos_novos': 0, 'erro': None,
    }):
        with patch.object(criar_admin.services, 'API_KEY', 'test-key'):
            criar_admin.criar_admin()

    with app.app_context():
        user = User.query.filter_by(username='admin-existing').first()
        concelhos = {
            uc.concelho for uc in UtilizadorConcelho.query.filter_by(user_id=user.id).all()
        }
        assert concelhos == {'Porto'}


def test_recolha_chamada_quando_nao_ha_postos(app, monkeypatch):
    """Recolha e chamada quando a tabela de postos esta vazia e ha chave API."""
    inputs = iter(['admin-teste', 'admin@exemplo.pt', 'password'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    monkeypatch.setattr(criar_admin, 'create_app', lambda env: app)

    with patch.object(criar_admin.services, 'atualizar_precos_se_necessario', return_value={
        'executado': True, 'sucesso': True, 'precos_novos': 10, 'erro': None,
    }) as mock_recolha:
        with patch.object(criar_admin.services, 'API_KEY', 'test-key'):
            _criar_admin(app, monkeypatch)

    mock_recolha.assert_called_once_with(forcar=True)


def test_recolha_nao_chamada_quando_ja_existem_postos(app, monkeypatch):
    """Recolha nao e chamada quando ja existem postos na BD."""
    with app.app_context():
        user = User(username='admin-teste', email='admin@exemplo.pt')
        user.password_hash = generate_password_hash('password')
        db.session.add(user)
        db.session.commit()

        db.session.add(Posto(id=1, nome='Posto Teste', concelho='Braga'))
        db.session.commit()

    inputs = iter(['admin-teste', 'admin@exemplo.pt', 'password'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    monkeypatch.setattr(criar_admin, 'create_app', lambda env: app)

    with patch.object(criar_admin.services, 'atualizar_precos_se_necessario') as mock_recolha:
        with patch.object(criar_admin.services, 'API_KEY', 'test-key'):
            _criar_admin(app, monkeypatch)

    mock_recolha.assert_not_called()


def test_erro_na_recolha_nao_impede_criacao(app, monkeypatch):
    """Erro na recolha nao impede a criacao do admin, listas nem concelhos."""
    inputs = iter(['admin-teste', 'admin@exemplo.pt', 'password'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    monkeypatch.setattr(criar_admin, 'create_app', lambda env: app)

    with patch.object(criar_admin.services, 'atualizar_precos_se_necessario', side_effect=Exception('API error')):
        with patch.object(criar_admin.services, 'API_KEY', 'test-key'):
            _criar_admin(app, monkeypatch)

    with app.app_context():
        user = User.query.filter_by(username='admin-teste').first()
        assert user is not None
        assert Lista.query.filter_by(user_id=user.id).count() == 4
        assert UtilizadorConcelho.query.filter_by(user_id=user.id).count() == 3


def test_sem_api_key_nao_recolhe(app, monkeypatch):
    """Sem APIABERTA_API_KEY definida, a recolha e saltada."""
    inputs = iter(['admin-teste', 'admin@exemplo.pt', 'password'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    monkeypatch.setattr(criar_admin, 'create_app', lambda env: app)

    with patch.object(criar_admin.services, 'atualizar_precos_se_necessario') as mock_recolha:
        with patch.object(criar_admin.services, 'API_KEY', None):
            _criar_admin(app, monkeypatch)

    mock_recolha.assert_not_called()
