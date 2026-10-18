"""Testes do canal Zoho Mail e do resultado de envio dos convites."""
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from unittest import mock

import pytest
import requests
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.auth.models import Convite, User
from app.notifications.models import UserNotificationPreferences
from app.notifications.channels.email import EmailChannel


TOKEN = 'access-sensivel'
SEGREDO = 'segredo-sensivel'
REFRESH = 'refresh-sensivel'
CONTEUDO = 'conteudo-privado'


@pytest.fixture
def app(tmp_path):
    """App de teste com BD em memória e cache Zoho isolada em pasta temporária."""
    app = create_app('testing')
    with app.app_context():
        assert 'memory' in str(db.engine.url)
        db.create_all()
        app.config.update(
            ZOHO_CLIENT_ID='id-teste', ZOHO_CLIENT_SECRET=SEGREDO,
            ZOHO_REFRESH_TOKEN=REFRESH, ZOHO_ACCOUNT_ID='conta-teste',
            ZOHO_FROM_EMAIL='PIPE <pipe@exemplo.pt>', ZOHO_DC='eu',
            ZOHO_TOKEN_CACHE_PATH=str(tmp_path / 'zoho-token.json'),
        )
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
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


def _canal(app, **kwargs):
    return EmailChannel(
        client_id=app.config['ZOHO_CLIENT_ID'],
        client_secret=app.config['ZOHO_CLIENT_SECRET'],
        refresh_token=app.config['ZOHO_REFRESH_TOKEN'],
        account_id=app.config['ZOHO_ACCOUNT_ID'],
        remetente=app.config['ZOHO_FROM_EMAIL'],
        dc=app.config['ZOHO_DC'],
        cache_path=app.config['ZOHO_TOKEN_CACHE_PATH'], **kwargs,
    )


def _resposta(codigo=200, corpo=None):
    resposta = mock.Mock(status_code=codigo)
    resposta.json.return_value = corpo or {
        'status': {'code': 200}, 'data': {'messageId': 'zoho-msg-123'}
    }
    return resposta


def _token_resposta(token=TOKEN):
    return _resposta(200, {'access_token': token, 'expires_in': 3600})


def _guardar_cache(canal, token=TOKEN, restante=3600):
    canal._guardar_cache(token, restante)


class TestCanalZoho:
    def test_sucesso_renova_sem_cache_e_envia_payload_zoho(self, app):
        canal = _canal(app)
        destino = mock.Mock(email='para@exemplo.pt')
        with mock.patch('app.notifications.channels.email.requests.post',
                        side_effect=[_token_resposta(), _resposta()]) as pedido:
            assert canal.enviar(destino, 'Assunto', CONTEUDO, html='<p>privado</p>')
        assert pedido.call_count == 2
        assert pedido.call_args_list[0].args[0] == 'https://accounts.zoho.eu/oauth/v2/token'
        envio = pedido.call_args_list[1]
        assert envio.args[0] == 'https://mail.zoho.eu/api/accounts/conta-teste/messages'
        assert envio.kwargs['headers']['Authorization'] == f'Zoho-oauthtoken {TOKEN}'
        assert envio.kwargs['headers']['Accept'] == 'application/json'
        assert envio.kwargs['json']['fromAddress'] == 'PIPE <pipe@exemplo.pt>'
        assert envio.kwargs['json']['mailFormat'] == 'html'
        assert envio.kwargs['timeout'] == 10
        assert canal.ultimo_resultado == {
            'sucesso': True, 'message_id': 'zoho-msg-123', 'erro': None
        }

    def test_reutiliza_cache_valida_sem_renovar(self, app):
        canal = _canal(app)
        _guardar_cache(canal)
        with mock.patch('app.notifications.channels.email.requests.post',
                        return_value=_resposta()) as pedido:
            assert canal.enviar(mock.Mock(email='para@exemplo.pt'), 'a', 'b')
        pedido.assert_called_once()
        assert pedido.call_args.args[0].startswith('https://mail.zoho.eu/')

    def test_cache_perto_da_expiracao_renova(self, app):
        canal = _canal(app)
        _guardar_cache(canal, restante=100)
        with mock.patch('app.notifications.channels.email.requests.post',
                        side_effect=[_token_resposta('novo-token'), _resposta()]) as pedido:
            assert canal.enviar(mock.Mock(email='para@exemplo.pt'), 'a', 'b')
        assert pedido.call_count == 2
        assert pedido.call_args_list[1].kwargs['headers']['Authorization'] == 'Zoho-oauthtoken novo-token'

    def test_falha_ao_gravar_cache_nao_impede_envio(self, app, monkeypatch):
        canal = _canal(app)
        monkeypatch.setattr('app.notifications.channels.email.os.replace',
                            mock.Mock(side_effect=OSError('disco indisponível')))
        with mock.patch('app.notifications.channels.email.requests.post',
                        side_effect=[_token_resposta(), _resposta()]):
            assert canal.enviar(mock.Mock(email='para@exemplo.pt'), 'a', 'b') is True

    def test_retry_unico_depois_de_token_invalido(self, app):
        canal = _canal(app)
        _guardar_cache(canal)
        invalido = _resposta(401, {'status': {'code': 401}, 'message': 'token'} )
        with mock.patch('app.notifications.channels.email.requests.post',
                        side_effect=[invalido, _token_resposta('renovado'), _resposta()]) as pedido:
            assert canal.enviar(mock.Mock(email='para@exemplo.pt'), 'a', 'b')
        assert pedido.call_count == 3

    def test_erro_no_corpo_devolve_falha(self, app, caplog):
        canal = _canal(app)
        _guardar_cache(canal)
        falha = _resposta(200, {
            'status': {'code': 500, 'description': 'Internal Error'},
            'data': {'moreInfo': 'Falha temporária do servidor Zoho'},
        })
        with caplog.at_level(logging.ERROR), mock.patch(
                'app.notifications.channels.email.requests.post', return_value=falha):
            assert canal.enviar(mock.Mock(email='para@exemplo.pt'), 'a', CONTEUDO) is False
        assert canal.ultimo_resultado['sucesso'] is False
        assert CONTEUDO not in caplog.text
        assert 'status.description=Internal Error' in caplog.text
        assert 'data.moreInfo=Falha temporária do servidor Zoho' in caplog.text

    def test_detalhes_zoho_no_log_redigem_dados_sensiveis_e_truncam(self, app, caplog):
        canal = _canal(app)
        _guardar_cache(canal)
        destinatario = 'destinatario-privado@exemplo.pt'
        assunto = 'ASSUNTO-PRIVADO'
        conteudo = 'CONTEUDO-PRIVADO'
        html = '<p>HTML-PRIVADO</p>'
        resposta = _resposta(500, {
            'status': {
                'code': 500,
                'description': f'Internal Error {SEGREDO} {REFRESH} {TOKEN} {assunto}',
            },
            'message': f'{destinatario} {conteudo} {html}',
            'data': {'moreInfo': f'Erro {SEGREDO} {REFRESH} {TOKEN} {destinatario} {assunto} {conteudo} {html}'},
        })
        utilizador = mock.Mock(email=destinatario)
        with caplog.at_level(logging.ERROR), mock.patch(
                'app.notifications.channels.email.requests.post', return_value=resposta):
            assert canal.enviar(utilizador, assunto, conteudo, html=html) is False

        for sensivel in (SEGREDO, REFRESH, TOKEN, destinatario, assunto, conteudo, html):
            assert sensivel not in caplog.text
        assert 'status.code=500' in caplog.text
        assert 'status.description=Internal Error' in caplog.text

        resumo = EmailChannel._resumo_resposta({'data': {'moreInfo': 'x' * 500}})
        assert len(resumo) == 300

    def test_falha_de_rede_nao_expoe_dados_sensiveis(self, app, caplog):
        canal = _canal(app)
        with caplog.at_level(logging.ERROR), mock.patch(
                'app.notifications.channels.email.requests.post',
                side_effect=requests.Timeout(f'{SEGREDO} {REFRESH} {TOKEN} {CONTEUDO}')):
            assert canal.enviar(mock.Mock(email='para@exemplo.pt'), 'a', CONTEUDO) is False
        for sensivel in (SEGREDO, REFRESH, TOKEN, CONTEUDO):
            assert sensivel not in caplog.text
        assert 'Timeout' in caplog.text

    def test_resposta_json_invalida_falha_sem_registar_corpo(self, app, caplog):
        canal = _canal(app)
        _guardar_cache(canal)
        invalida = mock.Mock(status_code=200)
        invalida.json.side_effect = ValueError('segredo de corpo')
        with caplog.at_level(logging.ERROR), mock.patch(
                'app.notifications.channels.email.requests.post', return_value=invalida):
            assert canal.enviar(mock.Mock(email='para@exemplo.pt'), 'a', CONTEUDO) is False
        assert 'segredo de corpo' not in caplog.text
        assert CONTEUDO not in caplog.text

    def test_falha_de_renovacao_nao_regista_segredos(self, app, caplog):
        canal = _canal(app)
        resposta = _resposta(400, {'error': 'invalid_client'})
        with caplog.at_level(logging.ERROR), mock.patch(
                'app.notifications.channels.email.requests.post', return_value=resposta):
            assert canal.enviar(mock.Mock(email='para@exemplo.pt'), 'a', CONTEUDO) is False
        for sensivel in (SEGREDO, REFRESH, TOKEN, CONTEUDO):
            assert sensivel not in caplog.text


def test_convite_guarda_resultado_e_message_id(admin_client):
    app = admin_client.application
    canal = _canal(app)
    _guardar_cache(canal)
    with mock.patch('app.notifications.channels.email.requests.post', return_value=_resposta()):
        resposta = admin_client.post('/admin/convites/gerar', json={
            'email': 'novo@exemplo.pt', 'enviar_email': True,
        })
    assert resposta.status_code == 200
    assert resposta.get_json()['email_enviado'] is True
    with app.app_context():
        convite = Convite.query.filter_by(email='novo@exemplo.pt').one()
        assert convite.email_estado == 'enviado'
        assert convite.email_message_id == 'zoho-msg-123'


def test_convite_sem_email_nao_guarda_estado(admin_client):
    resposta = admin_client.post('/admin/convites/gerar', json={
        'email': 'link@exemplo.pt', 'enviar_email': False,
    })
    assert resposta.status_code == 200
    with admin_client.application.app_context():
        convite = Convite.query.filter_by(email='link@exemplo.pt').one()
        assert convite.email_estado is None
        assert convite.email_message_id is None


def test_tabela_nao_expoe_consulta_de_entrega(admin_client):
    resposta = admin_client.get('/admin/convites')
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert 'verificarEstadoEmail' not in html
    assert 'urlEstadoEmail' not in html
    assert 'Mailjet' not in html


def test_rota_antiga_de_estado_foi_removida(admin_client):
    assert admin_client.get('/admin/convites/1/estado-email').status_code == 404


def test_teste_de_email_mostra_diagnostico_sem_segredos(admin_client, monkeypatch):
    with admin_client.application.app_context():
        utilizador = User.query.filter_by(username='admin-teste').one()
        db.session.add(UserNotificationPreferences(
            user_id=utilizador.id, email_activo=True,
        ))
        db.session.commit()

    def falhar(canal, *args, **kwargs):
        canal.ultimo_resultado = {
            'sucesso': False, 'message_id': None,
            'erro': 'envio: HTTP 403; código Zoho 5501',
        }
        return False

    monkeypatch.setattr(EmailChannel, 'enviar_template', falhar)
    resposta = admin_client.post('/definicoes/testar-email', follow_redirects=True)
    assert resposta.status_code == 200
    assert 'HTTP 403' in resposta.get_data(as_text=True)
    assert SEGREDO not in resposta.get_data(as_text=True)


def test_rota_de_teste_email_envia_com_respostas_zoho_mockadas(admin_client):
    with admin_client.application.app_context():
        utilizador = User.query.filter_by(username='admin-teste').one()
        db.session.add(UserNotificationPreferences(
            user_id=utilizador.id, email_activo=True,
        ))
        db.session.commit()

    with mock.patch('app.notifications.channels.email.requests.post',
                    side_effect=[_token_resposta(), _resposta()]) as pedido:
        resposta = admin_client.post('/definicoes/testar-email', follow_redirects=True)

    assert resposta.status_code == 200
    assert 'Email de teste enviado' in resposta.get_data(as_text=True)
    assert pedido.call_count == 2
