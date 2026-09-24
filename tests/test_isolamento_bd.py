"""Teste de regressão do guarda-civil de isolamento da BD (tests/conftest.py).

Garante que a salvaguarda que impede um `db.drop_all()` de correr contra uma BD
de ficheiro continua activa — foi exactamente esse acidente que apagou
`instance/pipe.db`.
"""
import os
import tempfile

import pytest

import config as config_mod
from app import create_app, db


def test_guard_bloqueia_drop_all_com_bd_de_ficheiro(monkeypatch):
    """Com uma BD de ficheiro, o drop_all tem de abortar antes de tocar nela."""
    caminho = os.path.join(tempfile.mkdtemp(prefix='pipe-guard-'), 'guard.db')

    class GuardConfig(config_mod.TestingConfig):
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + caminho
        SESSION_FILE_DIR = tempfile.mkdtemp(prefix='pipe-guard-session-')

    monkeypatch.setitem(config_mod.config, 'guard-test', GuardConfig)

    app = create_app('guard-test')
    with app.app_context():
        assert 'memory' not in str(db.engine.url)
        db.create_all()
        with pytest.raises(RuntimeError, match='ABORTADO'):
            db.drop_all()
        db.session.remove()
