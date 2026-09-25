"""Testes da confirmação de envio de email dos convites (Mailjet).

O painel mostrava «Convite enviado» só com base na aceitação da API — sem prova
de entrega. Estes testes cobrem: o regresso do MessageID no `enviar()`, o registo
do estado no convite, e o endpoint `/admin/convites/<id>/estado-email` que
consulta a actividade real do Mailjet (entregue / falhou + motivo do bounce).
"""
import os
import sys
from datetime import datetime, timedelta
from unittest import mock

import pytest
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.auth.models import Convite, User
from app.notifications.channels.email import EmailChannel

MESSAGE_ID = 1152921544892419067  # formato real do Mailjet (19 dígitos)


# ═════════ FIXTURES ═════════

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
        # Garantir que o endpoint de estado encontra o Mailjet configurado
        app.config['MAILJET_API_KEY'] = 'chave-teste'
        app.config['MAILJET_API_SECRET'] = 'segredo-teste'
        app.config['MAILJET_FROM_EMAIL'] = 'teste@exemplo.pt'
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """Cliente com sessão de administrador (CSRF desligado no TestingConfig)."""
    with client.application.app_context():
        user = User(username='admin-teste', email='admin@exemplo.pt')
        user.password_hash = generate_password_hash('password-de-teste-123')
        user.is_admin = True
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    with client.session_transaction() as sess:
        sess['_user_id'] = user_id
    return client


# ═════════ RESPOSTAS FALSAS DO MAILJET ═════════

def _resposta_envio(codigo=200, estado='success'):
    """Resposta de POST /v3.1/send."""
    r = mock.Mock(status_code=codigo)
    if estado == 'success':
        r.json.return_value = {'Messages': [{'Status': 'success',
                                             'To': [{'Email': 'para@exemplo.pt',
                                                     'MessageID': MESSAGE_ID}]}]}
    else:
        r.json.return_value = {'Messages': [{'Status': 'error',
                                             'ErrorMessage': 'Unable to connect to server'}]}
    return r


def _fake_get_entregue(url, *args, **kwargs):
    r = mock.Mock(status_code=200)
    if 'messagehistory' in url:
        r.json.return_value = {'Data': [
            {'EventAt': 1790324894, 'EventType': 'sent', 'Comment': ''},
            {'EventAt': 1790325000, 'EventType': 'delivered', 'Comment': ''},
        ]}
    else:
        r.json.return_value = {'Data': [{'Status': 'delivered'}]}
    return r


def _fake_get_softbounced(url, *args, **kwargs):
    r = mock.Mock(status_code=200)
    if 'messagehistory' in url:
        r.json.return_value = {'Data': [
            {'EventAt': 1790319683, 'EventType': 'softbounced',
             'Comment': '550 5.7.40 Your email has been blocked because the '
                        'From: header is not aligned with the authenticated '
                        'SPF or DKIM organizational domain.'},
        ]}
    else:
        r.json.return_value = {'Data': [{'Status': 'softbounced'}]}
    return r


# ═════════ CANAL EmailChannel ═════════

class TestCanalEmail:
    def test_enviar_extrai_message_id(self):
        canal = EmailChannel('k', 's', 'remetente@exemplo.pt')
        destino = mock.Mock(email='para@exemplo.pt')
        with mock.patch('app.notifications.channels.email.requests.post',
                        return_value=_resposta_envio()):
            assert canal.enviar(destino, 'Assunto', 'Corpo') is True
        assert canal.ultimo_resultado['sucesso'] is True
        assert canal.ultimo_resultado['message_id'] == MESSAGE_ID
        assert canal.ultimo_resultado['erro'] is None

    def test_enviar_falha_regista_motivo(self):
        canal = EmailChannel('k', 's', 'remetente@exemplo.pt')
        destino = mock.Mock(email='para@exemplo.pt')
        with mock.patch('app.notifications.channels.email.requests.post',
                        return_value=_resposta_envio(codigo=401)):
            assert canal.enviar(destino, 'Assunto', 'Corpo') is False
        assert canal.ultimo_resultado['sucesso'] is False
        assert canal.ultimo_resultado['message_id'] is None
        assert canal.ultimo_resultado['erro'] == 'HTTP 401'

    def test_enviar_sem_email_destinatario(self):
        canal = EmailChannel('k', 's', 'remetente@exemplo.pt')
        destino = mock.Mock(email=None)
        assert canal.enviar(destino, 'Assunto', 'Corpo') is False
        assert canal.ultimo_resultado['erro'] == 'Destinatário sem email.'

    def test_consultar_estado_entregue(self):
        canal = EmailChannel('k', 's', 'remetente@exemplo.pt')
        with mock.patch('app.notifications.channels.email.requests.get',
                        side_effect=_fake_get_entregue):
            res = canal.consultar_estado(MESSAGE_ID)
        assert res['erro'] is None
        assert res['estado'] == 'delivered'
        assert res['motivo'] is None
        assert [e['tipo'] for e in res['eventos']] == ['sent', 'delivered']
        assert res['eventos'][0]['quando'] != '?'

    def test_consultar_estado_softbounced_devolve_motivo(self):
        canal = EmailChannel('k', 's', 'remetente@exemplo.pt')
        with mock.patch('app.notifications.channels.email.requests.get',
                        side_effect=_fake_get_softbounced):
            res = canal.consultar_estado(MESSAGE_ID)
        assert res['erro'] is None
        assert res['estado'] == 'softbounced'
        assert '550 5.7.40' in res['motivo']

    def test_consultar_estado_http_401(self):
        canal = EmailChannel('k', 's', 'remetente@exemplo.pt')
        resposta = mock.Mock(status_code=401)
        with mock.patch('app.notifications.channels.email.requests.get',
                        return_value=resposta):
            res = canal.consultar_estado(MESSAGE_ID)
        assert res['erro'] == 'HTTP 401'
        assert res['estado'] is None


# ═════════ ROTA: gerar convite ═════════

class TestGerarConvite:
    def test_guarda_message_id_e_estado(self, admin_client):
        with mock.patch('app.notifications.channels.email.requests.post',
                        return_value=_resposta_envio()):
            r = admin_client.post('/admin/convites/gerar',
                                  json={'email': 'novo@exemplo.pt',
                                        'enviar_email': True})
        assert r.status_code == 200
        dados = r.get_json()
        assert dados['email_enviado'] is True
        assert dados['message_id'] == str(MESSAGE_ID)
        with admin_client.application.app_context():
            convite = Convite.query.filter_by(email='novo@exemplo.pt').one()
            assert convite.mailjet_message_id == str(MESSAGE_ID)
            assert convite.email_estado == 'aceite'

    def test_falha_mostra_motivo_e_marca_falhou(self, admin_client):
        with mock.patch('app.notifications.channels.email.requests.post',
                        return_value=_resposta_envio(estado='error')):
            r = admin_client.post('/admin/convites/gerar',
                                  json={'email': 'falha@exemplo.pt',
                                        'enviar_email': True})
        assert r.status_code == 500
        assert 'Unable to connect to server' in r.get_json()['erro']
        with admin_client.application.app_context():
            convite = Convite.query.filter_by(email='falha@exemplo.pt').one()
            assert convite.email_estado == 'falhou'
            assert convite.mailjet_message_id is None

    def test_sem_envio_de_email_nao_regista_estado(self, admin_client):
        r = admin_client.post('/admin/convites/gerar',
                              json={'email': 'link@exemplo.pt',
                                    'enviar_email': False})
        assert r.status_code == 200
        dados = r.get_json()
        assert dados['email_enviado'] is False
        with admin_client.application.app_context():
            convite = Convite.query.filter_by(email='link@exemplo.pt').one()
            assert convite.email_estado is None
            assert convite.mailjet_message_id is None


# ═════════ ROTA: estado do email ═════════

def _criar_convite(client, email, message_id=MESSAGE_ID):
    """Convite como fica depois de um envio aceite pelo Mailjet."""
    with client.application.app_context():
        admin = User.query.filter_by(username='admin-teste').first()
        convite = Convite(
            token=f'token-{email.replace("@", "-").replace(".", "-")}',
            email=email,
            criado_por=admin.id,
            expira_em=datetime.utcnow() + timedelta(days=7),
            mailjet_message_id=str(message_id) if message_id else None,
            email_estado='aceite' if message_id else None,
        )
        db.session.add(convite)
        db.session.commit()
        return convite.id


class TestEstadoEmail:
    def test_confirma_entregue_e_guarda_verificacao(self, admin_client):
        cid = _criar_convite(admin_client, 'verificar@exemplo.pt')
        with mock.patch('app.notifications.channels.email.requests.get',
                        side_effect=_fake_get_entregue):
            r = admin_client.get(f'/admin/convites/{cid}/estado-email')
        assert r.status_code == 200
        dados = r.get_json()
        assert dados['sucesso'] is True
        assert dados['estado'] == 'delivered'
        assert dados['rotulo'] == 'entregue'
        assert dados['classe'] == 'badge-activo'
        assert dados['motivo'] is None
        assert len(dados['eventos']) == 2
        with admin_client.application.app_context():
            convite = Convite.query.get(cid)
            assert convite.email_estado == 'delivered'
            assert convite.email_verificado_em is not None
            assert convite.estado_email() == ('entregue', 'badge-activo')

    def test_softbounced_mostra_motivo_e_rotulo_de_falha(self, admin_client):
        cid = _criar_convite(admin_client, 'rebentado@exemplo.pt')
        with mock.patch('app.notifications.channels.email.requests.get',
                        side_effect=_fake_get_softbounced):
            r = admin_client.get(f'/admin/convites/{cid}/estado-email')
        assert r.status_code == 200
        dados = r.get_json()
        assert dados['estado'] == 'softbounced'
        assert 'falhou' in dados['rotulo']
        assert dados['classe'] == 'badge-expirado'
        assert '550 5.7.40' in dados['motivo']

    def test_sem_message_id_devolve_400(self, admin_client):
        cid = _criar_convite(admin_client, 'sem-id@exemplo.pt', message_id=None)
        r = admin_client.get(f'/admin/convites/{cid}/estado-email')
        assert r.status_code == 400
        assert 'sem ID' in r.get_json()['erro']

    def test_consulta_com_falha_devolve_502_e_nao_grava(self, admin_client):
        cid = _criar_convite(admin_client, 'sem-api@exemplo.pt')
        resposta = mock.Mock(status_code=401)
        with mock.patch('app.notifications.channels.email.requests.get',
                        return_value=resposta):
            r = admin_client.get(f'/admin/convites/{cid}/estado-email')
        assert r.status_code == 502
        assert 'HTTP 401' in r.get_json()['erro']
        with admin_client.application.app_context():
            convite = Convite.query.get(cid)
            assert convite.email_verificado_em is None
            assert convite.email_estado == 'aceite'  # estado anterior preservado


class TestPaginaConvites:
    def test_tabela_renderiza_estado_e_botao_de_verificacao(self, admin_client):
        """A página nova tem a coluna do Mailjet, o badge e o botão 🔄."""
        _criar_convite(admin_client, 'render@exemplo.pt')
        r = admin_client.get('/admin/convites')
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert 'Email (Mailjet)' in html
        assert 'verificarEstadoEmail(' in html       # botão 🔄 com o id do convite
        assert 'urlEstadoEmail' in html              # JS de verificação presente
        assert '>enviado<' in html                   # badge do estado 'aceite'
        assert 'title="Mailjet ID' in html           # ID visível no hover


