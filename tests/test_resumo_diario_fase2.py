"""Testes das definições, pré-visualização e envio manual do Resumo Diário."""

from datetime import date
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.auth.models import User
from app.notifications.models import UserNotificationPreferences
from app.resumo_diario.models import ConfiguracaoResumoDiario
from app.resumo_diario.services import (
    OPCOES_POR_OMISSAO,
    gerar_resumo_diario,
    ler_configuracao_resumo_diario,
)


@pytest.fixture
def contexto():
    app = create_app('testing')
    with app.app_context():
        assert ':memory:' in app.config['SQLALCHEMY_DATABASE_URI']
        utilizador = User(username='resumo-f2', email='resumo-f2@example.test', password_hash='x')
        outro = User(username='resumo-f2-b', email='resumo-f2-b@example.test', password_hash='x')
        db.session.add_all([utilizador, outro])
        db.session.commit()
        ids = utilizador.id, outro.id
    cliente = app.test_client()
    with cliente.session_transaction() as sess:
        sess['_user_id'] = ids[0]
        sess['_fresh'] = True
    yield app, cliente, ids
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_leitura_sem_linha_devolve_defaults_sem_gravar(contexto):
    app, _, (user_id, _) = contexto
    with app.app_context():
        assert ler_configuracao_resumo_diario(user_id) == OPCOES_POR_OMISSAO
        assert ConfiguracaoResumoDiario.query.filter_by(user_id=user_id).count() == 0


def test_criacao_recupera_conflito_de_unicidade(contexto):
    from app.resumo_diario import services

    app, _, (user_id, _) = contexto
    linha_concorrente = SimpleNamespace(user_id=user_id)
    consulta = SimpleNamespace(first=lambda: None, one=lambda: linha_concorrente)
    @contextmanager
    def transacao_com_conflito():
        raise IntegrityError('INSERT', {}, Exception('unique constraint'))
        yield

    with app.app_context():
        with patch.object(services.ConfiguracaoResumoDiario, 'query') as query, \
                patch.object(services.db.session, 'begin_nested',
                             side_effect=transacao_com_conflito):
            query.filter_by.return_value = consulta
            assert services.obter_ou_criar_configuracao(user_id) is linha_concorrente


def test_get_da_pagina_nao_cria_linha_e_guardar_cria_isoladamente(contexto):
    app, cliente, (user_id, outro_id) = contexto
    resposta = cliente.get('/resumo-diario/definicoes')
    assert resposta.status_code == 200
    assert 'Pré-visualizar'.encode('utf-8') in resposta.data
    with app.app_context():
        assert ConfiguracaoResumoDiario.query.count() == 0

    resposta = cliente.post('/resumo-diario/definicoes', data={
        'meteorologia': 'on', 'eventos': 'on',
    }, follow_redirects=True)
    assert resposta.status_code == 200
    with app.app_context():
        assert ler_configuracao_resumo_diario(user_id) == {
            'meteorologia': True, 'tarefas': False, 'eventos': True,
            'combustiveis': False, 'fim_de_semana': False,
        }
        assert ler_configuracao_resumo_diario(outro_id) == OPCOES_POR_OMISSAO


def test_gerador_respeita_opcoes_guardadas(contexto):
    app, _, (user_id, _) = contexto
    with app.app_context():
        db.session.add(ConfiguracaoResumoDiario(
            user_id=user_id, meteorologia=False, tarefas=False,
            eventos=False, combustiveis=False, fim_de_semana=False))
        db.session.commit()
        with patch('app.resumo_diario.services.meteorologia_services.obter_previsao') as meteo, \
                patch('app.resumo_diario.services._tarefas_do_dia') as tarefas, \
                patch('app.resumo_diario.services._eventos_do_dia') as eventos, \
                patch('app.resumo_diario.services._combustiveis_do_utilizador') as combustiveis:
            resultado = gerar_resumo_diario(user_id, date(2026, 10, 6))
        meteo.assert_not_called()
        tarefas.assert_not_called()
        eventos.assert_not_called()
        combustiveis.assert_not_called()
        assert resultado['secoes'] == {}


def test_previsualizacao_nao_envia_nem_cria_configuracao(contexto):
    app, cliente, (user_id, _) = contexto
    with patch('app.resumo_diario.routes.gerar_resumo_diario',
               return_value={'data': '2026-10-08', 'texto': 'Resumo de teste'}) as gerar, \
            patch('app.resumo_diario.routes.notification_service.send') as enviar:
        resposta = cliente.post('/resumo-diario/api/previsualizar', json={})
    assert resposta.status_code == 200
    assert resposta.get_json()['texto'] == 'Resumo de teste'
    gerar.assert_called_once()
    enviar.assert_not_called()
    with app.app_context():
        assert ConfiguracaoResumoDiario.query.filter_by(user_id=user_id).count() == 0


def test_envio_sem_chat_id_mostra_mensagem_e_nao_chama_servico(contexto):
    _, cliente, _ = contexto
    with patch('app.resumo_diario.routes.notification_service.send') as enviar:
        resposta = cliente.post('/resumo-diario/api/enviar', json={})
    assert resposta.status_code == 400
    assert 'chat_id' in resposta.get_json()['mensagem']
    enviar.assert_not_called()


def test_envio_forca_telegram_com_chat_id_mesmo_com_canal_desligado(contexto):
    app, cliente, (user_id, _) = contexto
    with app.app_context():
        db.session.add(UserNotificationPreferences(
            user_id=user_id, telegram_chat_id='12345', telegram_activo=False))
        db.session.commit()

    with patch('app.resumo_diario.routes.gerar_resumo_diario',
               return_value={'data': '2026-10-08', 'texto': 'Resumo'}) as gerar, \
            patch('app.resumo_diario.routes.notification_service.send',
                  return_value={'telegram': True, 'email': None}) as enviar:
        resposta = cliente.post('/resumo-diario/api/enviar', json={})
    assert resposta.status_code == 200
    assert resposta.get_json()['ok'] is True
    gerar.assert_called_once()
    assert enviar.call_args.kwargs['force_channel'] == 'telegram'
    assert enviar.call_args.kwargs['telegram_parse_mode'] == 'HTML'


def test_servico_forcado_usa_so_telegram_sem_exigir_canal_activo(contexto):
    from app.notifications.service import NotificationService

    app, _, (user_id, _) = contexto

    class Canal:
        def __init__(self):
            self.chamadas = []

        def enviar(self, utilizador, assunto, corpo, dados=None, parse_mode='Markdown'):
            self.chamadas.append((utilizador.telegram_chat_id, parse_mode))
            return True

    with app.app_context():
        utilizador = db.session.get(User, user_id)
        db.session.add(UserNotificationPreferences(
            user_id=user_id, telegram_chat_id='12345', telegram_activo=False,
            email_activo=True))
        db.session.commit()
        canal_tg = Canal()
        canal_email = Canal()
        servico = NotificationService()
        servico._inicializado = True
        servico._canais = {'telegram': canal_tg, 'email': canal_email}

        resultado = servico.send(
            utilizador, 'resumo_diario', 'Resumo', 'Corpo',
            force_channel='telegram', telegram_parse_mode='HTML')

    assert resultado == {'telegram': True, 'email': None}
    assert canal_tg.chamadas == [('12345', 'HTML')]
    assert canal_email.chamadas == []


def test_texto_html_do_telegram_escapa_conteudo_de_utilizador():
    from app.notifications.channels.telegram import TelegramChannel

    class Resposta:
        status_code = 200

    class Utilizador:
        telegram_chat_id = '12345'

    with patch('app.notifications.channels.telegram.requests.post', return_value=Resposta()) as pedido:
        enviado = TelegramChannel('token').enviar(
            Utilizador(), 'Resumo <hoje> &', 'Título: A & B <C> _ *', parse_mode='HTML')
    assert enviado is True
    payload = pedido.call_args.kwargs['json']
    assert payload['parse_mode'] == 'HTML'
    assert payload['text'] == (
        '<b>Resumo &lt;hoje&gt; &amp;</b>\n\n'
        'Título: A &amp; B &lt;C&gt; _ *')


@pytest.mark.parametrize('caminho,metodo', [
    ('/resumo-diario/definicoes', 'get'),
    ('/resumo-diario/api/previsualizar', 'post'),
    ('/resumo-diario/api/enviar', 'post'),
])
def test_rotas_exigem_login(caminho, metodo):
    app = create_app('testing')
    resposta = getattr(app.test_client(), metodo)(caminho, json={} if metodo == 'post' else None)
    assert resposta.status_code == 302


def test_catalogo_mostra_resumo_diario(contexto):
    _, cliente, _ = contexto
    resposta = cliente.get('/modulos/loja')
    assert resposta.status_code == 200
    assert b'Resumo Di' in resposta.data


def test_previsualizacao_e_inserida_com_textcontent(contexto):
    _, cliente, _ = contexto
    resposta = cliente.get('/resumo-diario/definicoes')
    assert b'texto.textContent = resultado.dados.texto' in resposta.data
    assert b'texto.innerHTML' not in resposta.data


def test_limite_previsualizacao_dez_por_minuto(contexto):
    _, cliente, _ = contexto
    with patch('app.resumo_diario.routes.gerar_resumo_diario',
               return_value={'data': '2026-10-08', 'texto': 'Resumo'}):
        respostas = [cliente.post('/resumo-diario/api/previsualizar', json={})
                     for _ in range(11)]
    assert all(resposta.status_code == 200 for resposta in respostas[:10])
    assert respostas[10].status_code == 429


def test_limite_envio_cinco_por_hora(contexto):
    app, cliente, (user_id, _) = contexto
    with app.app_context():
        db.session.add(UserNotificationPreferences(
            user_id=user_id, telegram_chat_id='12345', telegram_activo=False))
        db.session.commit()
    with patch('app.resumo_diario.routes.gerar_resumo_diario',
               return_value={'data': '2026-10-08', 'texto': 'Resumo'}), \
            patch('app.resumo_diario.routes.notification_service.send',
                  return_value={'telegram': True, 'email': None}):
        respostas = [cliente.post('/resumo-diario/api/enviar', json={})
                     for _ in range(6)]
    assert all(resposta.status_code == 200 for resposta in respostas[:5])
    assert respostas[5].status_code == 429
