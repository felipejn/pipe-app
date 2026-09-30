"""Testes da distribuição da extensão Chrome do Cofre (download do ZIP + guia).

Sem alteração de BD — apenas rotas GET que servem o ZIP da pasta
`chrome-extension/` e o template HTML do guia de instalação.
"""
import io
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db


@pytest.fixture
def app():
    """App de teste com SQLite in-memory (nunca toca em instance/pipe.db)."""
    app = create_app('testing')

    with app.app_context():
        uri = str(db.engine.url)
        assert 'memory' in uri, (
            f'ABORTADO: os testes estão a apontar para a BD real ({uri}). '
            'Verificar SQLALCHEMY_DATABASE_URI em TestingConfig.'
        )
        db.create_all()
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    """Utilizador autenticado para testes."""
    from app.auth.models import User
    from werkzeug.security import generate_password_hash

    with client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        if not user:
            user = User(username='testuser', email='test@example.com')
            user.password_hash = generate_password_hash('testpass123')
            db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess['_user_id'] = user_id

    return client


# ═══════ DOWNLOAD DO ZIP ═══════

class TestDownloadExtensao:
    def test_download_devolve_zip(self, authenticated_client):
        r = authenticated_client.get('/passwords/extensao/download')
        assert r.status_code == 200
        assert 'zip' in r.content_type
        assert 'pipe-cofre-extensao' in r.headers.get('Content-Disposition', '')

    def test_zip_contem_ficheiros_da_extensao(self, authenticated_client):
        """O ZIP tem de conter a pasta chrome-extension/ com o manifest e os ficheiros."""
        r = authenticated_client.get('/passwords/extensao/download')
        assert r.status_code == 200

        with zipfile.ZipFile(io.BytesIO(r.data)) as zf:
            nomes = zf.namelist()
            # Prefixo para que, ao descompactar, fique a pasta certa (Load unpacked)
            assert 'chrome-extension/manifest.json' in nomes
            for esperado in (
                'chrome-extension/background.js',
                'chrome-extension/popup.html',
                'chrome-extension/popup.js',
                'chrome-extension/content.js',
                'chrome-extension/icon48.png',
                'chrome-extension/icon128.png',
            ):
                assert esperado in nomes, f'em falta no ZIP: {esperado}'
            # Nada de lixo no ZIP
            assert not any('__pycache__' in n for n in nomes)

    def test_manifest_no_zip_e_valido(self, authenticated_client):
        """O manifest.json dentro do ZIP tem de ser JSON válido e MV3."""
        import json
        r = authenticated_client.get('/passwords/extensao/download')
        with zipfile.ZipFile(io.BytesIO(r.data)) as zf:
            manifesto = json.loads(zf.read('chrome-extension/manifest.json'))
        assert manifesto['manifest_version'] == 3
        assert manifesto['version']

    def test_download_requer_sessao(self, client):
        """Sem sessão → redirect para o login (nunca o ZIP)."""
        r = client.get('/passwords/extensao/download')
        assert r.status_code == 302
        assert '/auth/login' in r.headers.get('Location', '')


# ═══════ PÁGINA DO GUIA ═══════

class TestGuiaExtensao:
    def test_guia_devolve_200(self, authenticated_client):
        r = authenticated_client.get('/passwords/extensao/guia')
        assert r.status_code == 200

    def test_guia_conteudo_essencial(self, authenticated_client):
        """A página tem de guiar para o download e conter os passos críticos."""
        r = authenticated_client.get('/passwords/extensao/guia')
        html = r.get_data(as_text=True)
        assert 'Load unpacked' in html
        assert 'COFRE_CORS_ORIGINS' in html
        assert '/passwords/extensao/download' in html
        assert 'Guia da extensão' in html

    def test_guia_requer_sessao(self, client):
        r = client.get('/passwords/extensao/guia')
        assert r.status_code == 302
        assert '/auth/login' in r.headers.get('Location', '')


# ═══════ ENTRY POINT NA PÁGINA DO MÓDULO ═══════

class TestEntryPointPaginaPasswords:
    def test_pagina_passwords_link_guia_e_download(self, authenticated_client):
        """A página do módulo tem de expor os botões de download e do guia."""
        r = authenticated_client.get('/passwords/')
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert '/passwords/extensao/download' in html
        assert '/passwords/extensao/guia' in html
        assert 'Extensão Chrome' in html
