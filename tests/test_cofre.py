"""Testes para o módulo Cofre de Passwords."""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.passwords.crypto import (
    gerar_salt, derivar_chave, hash_password_mestre,
    verificar_password_mestre, cifrar, decifrar,
    bytes_para_b64, b64_para_bytes
)
from app.passwords.models import CofreConfig, CofrePassword, extrair_dominio
from app.passwords import bp


@pytest.fixture
def app():
    """Cria app de teste com SQLite in-memory (nunca toca em instance/pipe.db).

    NOTA: a config tem de vir de `create_app('testing')` (TestingConfig) e não
    de atribuições a `app.config` depois do app criado — o engine do SQLAlchemy
    é fixado em `db.init_app()`, pelo que reescrever o URI a seguir não tem
    efeito e os testes acabam a apagar a BD real.
    """
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
    """Cria um utilizador autenticado para testes."""
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


# ═══════ CRYPTO ═══════

class TestCrypto:
    def test_gerar_salt_returns_base64(self):
        salt = gerar_salt()
        assert isinstance(salt, str)
        assert len(salt) > 0
        # Base64 de 32 bytes → 44 chars com padding
        import base64
        decoded = base64.b64decode(salt)
        assert len(decoded) == 32

    def test_derivar_chave_consistente(self):
        salt = gerar_salt()
        chave1 = derivar_chave('password123', salt)
        chave2 = derivar_chave('password123', salt)
        assert chave1 == chave2
        assert len(chave1) == 32  # AES-256

    def test_derivar_chave_different_passwords(self):
        salt = gerar_salt()
        chave1 = derivar_chave('password123', salt)
        chave2 = derivar_chave('different', salt)
        assert chave1 != chave2

    def test_hash_password_mestre(self):
        h = hash_password_mestre('masterpass')
        assert isinstance(h, str)
        assert h.startswith('$2')  # bcrypt prefix

    def test_verificar_password_mestre(self):
        h = hash_password_mestre('masterpass')
        assert verificar_password_mestre('masterpass', h) is True
        assert verificar_password_mestre('wrong', h) is False

    def test_cifrar_decifrar(self):
        chave = b'x' * 32  # 32 bytes para AES-256
        texto = 'Hello World'
        ct, iv, tag = cifrar(chave, texto)
        assert len(iv) == 12
        assert len(tag) == 16
        result = decifrar(chave, ct, iv, tag)
        assert result == texto

    def test_bytes_para_b64_roundtrip(self):
        data = b'test data'
        b64 = bytes_para_b64(data)
        assert isinstance(b64, str)
        assert b64_para_bytes(b64) == data


# ═══════ MODELOS ═══════

class TestExtrairDominio:
    def test_urlparse_hostname(self):
        assert extrair_dominio('https://www.exemplo.com/path') == 'exemplo.com'

    def test_www_strip(self):
        assert extrair_dominio('https://www.GOOGLE.com') == 'google.com'

    def test_com_maiusculas(self):
        assert extrair_dominio('https://WWW.EXEMPLO.COM') == 'exemplo.com'

    def test_com_porta(self):
        assert extrair_dominio('https://exemplo.com:8080/path') == 'exemplo.com'

    def test_sem_dominio(self):
        assert extrair_dominio('') is None
        assert extrair_dominio('https:///') is None

    def test_consistencia(self):
        """www.Exemplo.com, EXEMPLO.COM, exemplo.com devem dar o mesmo resultado."""
        urls = [
            'https://www.Exemplo.com/user',
            'https://EXEMPLO.COM:8080',
            'https://exemplo.com',
        ]
        resultados = {extrair_dominio(u) for u in urls}
        assert len(resultados) == 1, f"Expected 1 domain, got {resultados}"


class TestModels:
    def test_criar_cofre_config(self, authenticated_client):
        with authenticated_client.application.app_context():
            cofre = CofreConfig(
                user_id=1,
                master_pw_hash='$2b$12$abcdefghijklmnopqrstuv',
                salt=gerar_salt(),
                kdf_iterations=600000,
                ativo=True,
            )
            db.session.add(cofre)
            db.session.commit()
            assert cofre.id == 1
            assert cofre.ativo is True

    def test_criar_cofre_password(self, authenticated_client):
        with authenticated_client.application.app_context():
            entrada = CofrePassword(
                user_id=1,
                titulo='Teste',
                url='https://example.com',
                dominio='example.com',
                username='user1',
                password_cifrada=b'test_ct',
                iv=b'test_iv',
                tag=b'test_tag',
            )
            db.session.add(entrada)
            db.session.commit()
            assert entrada.id == 1

    def test_para_dict_com_chave(self, authenticated_client):
        with authenticated_client.application.app_context():
            chave = b'x' * 32
            ct, iv, tag = cifrar(chave, 'minha_password')
            entrada = CofrePassword(
                user_id=1,
                titulo='Teste',
                password_cifrada=ct,
                iv=iv,
                tag=tag,
            )
            db.session.add(entrada)
            db.session.commit()

            d = entrada.para_dict(chave)
            assert d['password'] == 'minha_password'

    def test_para_dict_sem_chave(self, authenticated_client):
        with authenticated_client.application.app_context():
            entrada = CofrePassword(
                user_id=1,
                titulo='Teste',
                password_cifrada=b'test',
                iv=b'test_iv',
                tag=b'test_tag',
            )
            db.session.add(entrada)
            db.session.commit()

            d = entrada.para_dict()
            assert 'password' not in d


# ═══════ API ═══════

class TestAPI:
    def test_estado_sem_cofre(self, authenticated_client):
        r = authenticated_client.get('/passwords/api/cofre/estado')
        assert r.status_code == 200
        data = r.get_json()
        assert data['activado'] is False
        assert data['desbloqueado'] is False

    def test_api_csrf_token(self, authenticated_client):
        r = authenticated_client.get('/passwords/api/csrf-token')
        assert r.status_code == 200
        data = r.get_json()
        assert 'csrfToken' in data

    def test_csrf_token_aceite_em_post_com_csrf_activo(self):
        """Regressão: o endpoint tem de devolver o token CSRF *assinado*.

        Com CSRF activo, o POST /passwords/api/gerar tem de ser aceite com o
        token devolvido por GET /passwords/api/csrf-token. Antes da correcção
        o endpoint devolvia `session['csrf_token']` (valor cru, vazio na
        primeira visita da sessão) e todas as acções do cofre — incluindo o
        gerador — falhavam com 400 e mostravam "Erro".
        """
        from app.auth.models import User
        from werkzeug.security import generate_password_hash

        app = create_app('testing')
        app.config['WTF_CSRF_ENABLED'] = True  # CSRFProtect lê a config em cada pedido

        with app.app_context():
            db.create_all()
            user = User(username='csrfuser', email='csrf@example.com')
            user.password_hash = generate_password_hash('testpass123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)

        r = client.get('/passwords/api/csrf-token')
        assert r.status_code == 200
        token = r.get_json()['csrfToken']
        assert token, 'o token CSRF não pode vir vazio'

        r2 = client.post(
            '/passwords/api/gerar',
            json={'modo': 'password', 'comprimento': 16},
            headers={'X-CSRFToken': token},
        )
        assert r2.status_code == 200, r2.get_data(as_text=True)
        assert len(r2.get_json()['valor']) == 16

        with app.app_context():
            db.session.remove()

    def test_activar_cofre(self, authenticated_client):
        r = authenticated_client.post('/passwords/api/cofre/activar',
            json={'password': 'masterpass123', 'confirmacao': 'masterpass123'})
        assert r.status_code == 200
        data = r.get_json()
        assert 'mensagem' in data

    def test_activar_cofre_password_curta(self, authenticated_client):
        r = authenticated_client.post('/passwords/api/cofre/activar',
            json={'password': 'short', 'confirmacao': 'short'})
        assert r.status_code == 400

    def test_activar_cofre_nao_confere(self, authenticated_client):
        r = authenticated_client.post('/passwords/api/cofre/activar',
            json={'password': 'pass1234', 'confirmacao': 'pass5678'})
        assert r.status_code == 400

    def test_desbloquear_sem_cofre(self, authenticated_client):
        r = authenticated_client.post('/passwords/api/cofre/desbloquear',
            json={'password': 'masterpass123'})
        assert r.status_code == 404

    def test_listar_entradas_bloqueado(self, authenticated_client):
        r = authenticated_client.get('/passwords/api/cofre/entradas')
        assert r.status_code == 401

    def test_criar_entrada_bloqueado(self, authenticated_client):
        r = authenticated_client.post('/passwords/api/cofre/entradas',
            json={'titulo': 'Teste', 'password': 'test'})
        assert r.status_code == 401


# ═══════ FLUXO COMPLETO DAS ENTRADAS ═══════

class TestFluxoEntradas:
    """Caminho felizes das entradas: activar → criar → listar → editar → apagar.

    Cobertura que faltava: um `NameError: datetime` no PUT só foi detectado a
    testar manualmente no browser, porque a suite apenas cobria os casos de
    cofre bloqueado.
    """

    def test_ciclo_completo_entrada(self, authenticated_client):
        c = authenticated_client

        r = c.post('/passwords/api/cofre/activar',
                   json={'password': 'master1234', 'confirmacao': 'master1234'})
        assert r.status_code == 200

        r = c.post('/passwords/api/cofre/entradas', json={
            'titulo': 'GitHub',
            'url': 'https://www.GitHub.com/login',
            'username': 'eu',
            'password': 'segredo123',
        })
        assert r.status_code == 200
        entrada_id = r.get_json()['id']

        entradas = c.get('/passwords/api/cofre/entradas').get_json()
        assert len(entradas) == 1
        assert entradas[0]['dominio'] == 'github.com'
        assert entradas[0]['password'] == 'segredo123'

        # Lookup da extensão: envia a URL completa, o servidor extrai o domínio
        filtradas = c.get('/passwords/api/cofre/entradas?url=https://github.com/settings').get_json()
        assert len(filtradas) == 1

        # Editar — regressão do NameError (import de datetime) e do domínio,
        # que tem de acompanhar a URL editada
        r = c.put(f'/passwords/api/cofre/entradas/{entrada_id}', json={
            'titulo': 'GitLab',
            'url': 'https://gitlab.com/users/sign_in',
            'username': 'eu',
            'password': 'nova12345',
        })
        assert r.status_code == 200, r.get_data(as_text=True)

        editada = c.get('/passwords/api/cofre/entradas').get_json()[0]
        assert editada['titulo'] == 'GitLab'
        assert editada['dominio'] == 'gitlab.com'
        assert editada['password'] == 'nova12345'

        # Bloquear → listagem recusada → desbloquear
        assert c.post('/passwords/api/cofre/bloquear').status_code == 200
        assert c.get('/passwords/api/cofre/entradas').status_code == 401
        assert c.post('/passwords/api/cofre/desbloquear',
                      json={'password': 'master1234'}).status_code == 200

        # Apagar
        assert c.delete(f'/passwords/api/cofre/entradas/{entrada_id}').status_code == 200
        assert c.get('/passwords/api/cofre/entradas').get_json() == []


# ═══════ SESSÃO E CHAVE DO COFRE ═══════

class TestSessaoCofre:
    """Expiração da chave do cofre e iterações da KDF."""

    def test_expiracao_do_cofre_bloqueia_sem_deslogar(self, authenticated_client):
        """Regressão: expirar a chave do cofre não pode apagar a sessão de login.

        `_obter_chave_cofre()` fazia `session.clear()` ao expirar, o que apagava
        também o `_user_id` do Flask-Login e deslogava o utilizador.
        """
        c = authenticated_client
        assert c.post('/passwords/api/cofre/activar',
                      json={'password': 'master1234', 'confirmacao': 'master1234'}).status_code == 200

        # Força a expiração: chave obtida há 10s com timeout de 5s (não usar
        # timeout 0 — no Windows time.time() tem granularidade de ~15,6 ms e a
        # comparação estrita podia não expirar)
        with c.session_transaction() as sess:
            sess['cofre_chave_ts'] = time.time() - 10
        c.application.config['COFRE_SESSION_TIMEOUT'] = 5
        assert c.get('/passwords/api/cofre/entradas').status_code == 401

        # Continua autenticado: o dashboard (login_required) responde 200 em vez
        # de redireccionar para o login
        assert c.get('/').status_code == 200

        # E o cofre volta a desbloquear normalmente
        c.application.config['COFRE_SESSION_TIMEOUT'] = 900
        assert c.post('/passwords/api/cofre/desbloquear',
                      json={'password': 'master1234'}).status_code == 200
        assert c.get('/passwords/api/cofre/entradas').status_code == 200

    def test_iteracoes_kdf_vem_da_config(self, authenticated_client):
        """COFRE_KDF_ITERATIONS tem de ser usado no activar, desbloquear e alterar.

        Com 1000 iterações em vez de 600 000 o teste corre em milissegundos e
        prova que a chave derivada é coerente com o `kdf_iterations` guardado:
        uma entrada criada antes de bloquear continua a decifrar depois.
        """
        from app.passwords.models import CofreConfig

        c = authenticated_client
        c.application.config['COFRE_KDF_ITERATIONS'] = 1000

        assert c.post('/passwords/api/cofre/activar',
                      json={'password': 'master1234', 'confirmacao': 'master1234'}).status_code == 200

        with c.application.app_context():
            assert CofreConfig.query.first().kdf_iterations == 1000

        assert c.post('/passwords/api/cofre/entradas', json={
            'titulo': 'GitHub', 'url': 'https://github.com', 'username': 'eu',
            'password': 'segredo123',
        }).status_code == 200

        assert c.post('/passwords/api/cofre/bloquear').status_code == 200
        assert c.post('/passwords/api/cofre/desbloquear',
                      json={'password': 'master1234'}).status_code == 200

        assert c.get('/passwords/api/cofre/entradas').get_json()[0]['password'] == 'segredo123'

        # Alterar a password mestra re-cifra tudo mantendo as iterações da config
        assert c.post('/passwords/api/cofre/alterar-password', json={
            'password_actual': 'master1234',
            'nova_password': 'outra12345',
            'confirmacao': 'outra12345',
        }).status_code == 200

        with c.application.app_context():
            assert CofreConfig.query.first().kdf_iterations == 1000

        assert c.get('/passwords/api/cofre/entradas').get_json()[0]['password'] == 'segredo123'


# ═══════ DEDUPLICAÇÃO ═══════

class TestDeduplicacao:
    def test_dominio_filtro_consistente(self, authenticated_client):
        """Verifica que a dedup funciona com domínios normalizados."""
        with authenticated_client.application.app_context():
            # Criar CofreConfig
            cofre = CofreConfig(
                user_id=1,
                master_pw_hash='$2b$12$abcdefghijklmnopqrstuv',
                salt=gerar_salt(),
                kdf_iterations=600000,
                ativo=True,
            )
            db.session.add(cofre)
            db.session.commit()

            # Criar entrada com www.exemplo.com
            ct, iv, tag = cifrar(b'x' * 32, 'pass1')
            entrada1 = CofrePassword(
                user_id=1, dominio='exemplo.com', username='user1',
                password_cifrada=ct, iv=iv, tag=tag,
            )
            db.session.add(entrada1)
            db.session.commit()

            # Tentar criar com EXEMPLO.com + mesmo username → deve ser duplicado
            # O filtro usa dominio='exemplo.com' que já existe
            existente = CofrePassword.query.filter_by(
                user_id=1, dominio='exemplo.com', username='user1'
            ).first()
            assert existente is not None

            # Domínio diferente → não é duplicado
            existente2 = CofrePassword.query.filter_by(
                user_id=1, dominio='google.com', username='user1'
            ).first()
            assert existente2 is None

    def test_extrair_dominio_csv_import(self):
        """Simula o fluxo de importação CSV."""
        urls = [
            'https://www.google.com/accounts',
            'https://google.com',
            'https://github.com/user/repo',
        ]
        dominios = {extrair_dominio(u) for u in urls}
        assert 'www.google.com' not in dominios  # www deve ser stripado
        assert 'google.com' in dominios
        assert 'github.com' in dominios
        assert len(dominios) == 2  # google.com + github.com


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
