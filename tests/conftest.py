"""Guarda-civil dos testes: nenhum teste pode tocar na BD real do PIPE.

Contexto: uma corrida de `tests/test_cofre.py` apagou todas as tabelas de
`instance/pipe.db`. O teste criava o app com a config real (`create_app()`),
reescrevia `SQLALCHEMY_DATABASE_URI` para `sqlite:///:memory:` **depois** de o
app existir e chamava `db.drop_all()`. O engine do SQLAlchemy é fixado em
`db.init_app()`, pelo que essa reescrita não tem efeito: o `drop_all()` correu
contra o ficheiro real.

A salvaguarda abaixo faz o teste falhar antes de qualquer `drop_all()` com BD
de ficheiro, mesmo que um ficheiro de teste futuro volte ao anti-padrão.
"""
import os
import sys

import flask_sqlalchemy
import pytest
from flask import current_app

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _proteger_bd_real(monkeypatch):
    original_drop_all = flask_sqlalchemy.SQLAlchemy.drop_all

    def drop_all_seguro(self, *args, **kwargs):
        uri = str(current_app.config.get('SQLALCHEMY_DATABASE_URI', ''))
        if ':memory:' not in uri:
            raise RuntimeError(
                f'ABORTADO: db.drop_all() com BD de ficheiro ({uri}). '
                "Os testes têm de usar create_app('testing') (SQLite em memória)."
            )
        return original_drop_all(self, *args, **kwargs)

    monkeypatch.setattr(flask_sqlalchemy.SQLAlchemy, 'drop_all', drop_all_seguro)
    yield
