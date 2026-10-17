"""Regressions for authentication, response headers, and upload limits."""
import base64
import io

import pyotp
import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.auth.models import User


@pytest.fixture
def client(monkeypatch):
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        user = User(
            username='security-test', email='security@example.com',
            password_hash=generate_password_hash('correct-horse-battery'),
            activo=True,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    yield app.test_client(), app, user_id
    with app.app_context():
        db.session.remove()


def test_production_requires_secret_key(monkeypatch):
    import config as app_config

    monkeypatch.setattr(app_config.ProductionConfig, 'SECRET_KEY', None)
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        create_app('production')


def test_security_headers_include_csp_and_hsts_only_in_production(client):
    test_client, app, _ = client
    resposta = test_client.get('/')
    assert 'Content-Security-Policy' in resposta.headers
    assert 'object-src \'none\'' in resposta.headers['Content-Security-Policy']
    assert 'Strict-Transport-Security' not in resposta.headers

    app.config['SESSION_COOKIE_SECURE'] = True
    resposta = test_client.get('/')
    assert resposta.headers['Strict-Transport-Security'] == 'max-age=31536000'


def test_inactive_account_cannot_reuse_existing_session(client):
    test_client, app, user_id = client
    with app.app_context():
        db.session.get(User, user_id).activo = False
        db.session.commit()
        from app.auth.models import load_user
        assert db.session.get(User, user_id).activo is False
        assert load_user(str(user_id)) is None

    with test_client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True

    resposta = test_client.get('/passwords/api/cofre/estado')
    assert resposta.status_code == 302
    assert '/auth/login' in resposta.headers['Location']


def test_external_next_is_ignored_and_remember_checkbox_is_respected(client):
    test_client, _, _ = client
    resposta = test_client.post(
        '/auth/login?next=https://attacker.example/phishing',
        data={'email': 'security@example.com', 'password': 'correct-horse-battery'},
    )
    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/')
    assert 'remember_token=' not in resposta.headers.get('Set-Cookie', '')
    with test_client.session_transaction() as sess:
        assert not sess.permanent


def test_internal_next_survives_login_form_submission(client):
    test_client, _, _ = client
    resposta = test_client.post(
        '/auth/login?next=/passwords/',
        data={'email': 'security@example.com', 'password': 'correct-horse-battery'},
    )
    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/passwords/')


def test_login_usa_email_e_ignora_maiusculas(client):
    test_client, _, _ = client
    resposta = test_client.post('/auth/login', data={
        'email': ' SECURITY@EXAMPLE.COM ',
        'password': 'correct-horse-battery',
    })
    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/')


def test_perfil_guarda_nome_e_apelido(client):
    test_client, app, user_id = client
    with test_client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True

    resposta = test_client.post('/auth/perfil', data={
        'dados-nome': 'Ana',
        'dados-apelido': 'Silva',
        'dados-submeter': 'Guardar dados',
    })
    assert resposta.status_code == 302
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.nome_completo == 'Ana Silva'


def test_remember_checkbox_sets_thirty_day_session(client):
    test_client, app, _ = client
    resposta = test_client.post(
        '/auth/login',
        data={
            'email': 'security@example.com', 'password': 'correct-horse-battery',
            'lembrar': 'y',
        },
    )
    assert resposta.status_code == 302
    assert 'remember_token=' in resposta.headers.get('Set-Cookie', '')
    with test_client.session_transaction() as sess:
        assert sess.permanent
    assert app.config['REMEMBER_COOKIE_DURATION'].days == 30


def test_totp_login_completes_and_honours_remember_choice(client):
    test_client, app, user_id = client
    secret = pyotp.random_base32()
    with app.app_context():
        user = db.session.get(User, user_id)
        user.totp_secret = secret
        user.totp_activo = True
        db.session.commit()
        assert user.metodos_2fa_activos() == ['totp']

    inicio = test_client.post(
        '/auth/login',
        data={
            'email': 'security@example.com', 'password': 'correct-horse-battery',
            'lembrar': 'y',
        },
    )
    assert '/2fa/enviar/totp' in inicio.headers['Location']
    pagina = test_client.get(inicio.headers['Location'])
    assert '/2fa/verificar' in pagina.headers['Location']

    resposta = test_client.post('/auth/2fa/verificar', data={
        'codigo': pyotp.TOTP(secret).now(),
    })
    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/')
    assert 'remember_token=' in resposta.headers.get('Set-Cookie', '')


def test_resend_2fa_is_rate_limited(client, monkeypatch):
    test_client, app, user_id = client
    with app.app_context():
        user = db.session.get(User, user_id)
        user.dois_fa_email_activo = True
        db.session.commit()
    monkeypatch.setattr('app.auth.routes._enviar_codigo_email', lambda _user: True)
    with test_client.session_transaction() as sess:
        sess['2fa_user_id'] = user_id
        sess['2fa_metodo'] = 'email'

    respostas = [test_client.post('/auth/2fa/reenviar') for _ in range(6)]
    assert all(r.status_code == 302 for r in respostas[:5])
    assert respostas[5].status_code == 429


def test_initial_2fa_delivery_is_rate_limited(client, monkeypatch):
    test_client, app, user_id = client
    with app.app_context():
        user = db.session.get(User, user_id)
        user.dois_fa_email_activo = True
        db.session.commit()
    monkeypatch.setattr('app.auth.routes._enviar_codigo_email', lambda _user: True)
    with test_client.session_transaction() as sess:
        sess['2fa_user_id'] = user_id

    respostas = [test_client.get('/auth/2fa/enviar/email') for _ in range(6)]
    assert all(r.status_code == 302 for r in respostas[:5])
    assert respostas[5].status_code == 429


def test_converter_rejeita_total_de_upload_acima_do_limite(client):
    test_client, app, user_id = client
    app.config['MAX_UPLOAD_TOTAL_BYTES'] = 4
    with test_client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True

    resposta = test_client.post('/conversoes/api/converter', data={
        'tipo': 'ico',
        'ficheiros': [
            (io.BytesIO(b'abc'), 'a.png'),
            (io.BytesIO(b'def'), 'b.png'),
        ],
    }, content_type='multipart/form-data')
    assert resposta.status_code == 413
    assert '50 MB' in resposta.get_json()['erro']


def test_conversor_rejeita_imagem_com_dimensoes_excessivas(monkeypatch):
    from app.conversoes import routes as conversoes

    class ImagemGrande:
        width = 5001
        height = 5000

    monkeypatch.setattr(conversoes.Image, 'open', lambda _conteudo: ImagemGrande())
    with pytest.raises(ValueError, match='25 milhões de píxeis'):
        conversoes.converter_img_para_ico(io.BytesIO(b'imagem'))


def test_conversor_ico_usa_redimensionamento_compatível_com_pillow_atual():
    from PIL import Image
    from app.conversoes.routes import converter_img_para_ico

    imagem = Image.new('RGB', (2, 2), color='red')
    origem = io.BytesIO()
    imagem.save(origem, format='PNG')
    origem.seek(0)

    resultado = converter_img_para_ico(origem)
    assert resultado.read(4) == b'\x00\x00\x01\x00'


def test_importacao_csv_rejeita_ficheiro_acima_do_limite(client):
    test_client, app, user_id = client
    app.config['MAX_CSV_BYTES'] = 4
    with test_client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True
        sess['cofre_chave'] = base64.b64encode(b'x' * 32).decode('ascii')
        sess['cofre_chave_ts'] = 9_999_999_999

    resposta = test_client.post('/passwords/api/cofre/importar-csv', data={
        'ficheiro': (io.BytesIO(b'12345'), 'passwords.csv'),
    }, content_type='multipart/form-data')
    assert resposta.status_code == 413


def test_importacao_csv_rejeita_demasiadas_linhas_sem_gravar_parcial(client):
    test_client, app, user_id = client
    app.config['MAX_CSV_ROWS'] = 1
    with test_client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True
        sess['cofre_chave'] = base64.b64encode(b'x' * 32).decode('ascii')
        sess['cofre_chave_ts'] = 9_999_999_999

    conteudo = (
        'name,url,username,password\n'
        'A,https://a.example,alice,one\n'
        'B,https://b.example,bob,two\n'
    )
    resposta = test_client.post('/passwords/api/cofre/importar-csv', data={
        'ficheiro': (io.BytesIO(conteudo.encode()), 'passwords.csv'),
    }, content_type='multipart/form-data')
    assert resposta.status_code == 413
    with app.app_context():
        from app.passwords.models import CofrePassword
        assert CofrePassword.query.filter_by(user_id=user_id).count() == 0
