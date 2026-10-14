"""Testes do canal Telegram — motivo da falha e retry em falhas transitórias.

Contexto: em 14/10/2026 a scheduled task não entregou o Resumo Diário e o log
dizia apenas `telegram=False`. Esse valor não distinguia «sem chat_id» de
«a API rejeitou» de «a rede falhou» — e o motivo exacto (HTTP + `description`
da Bot API) era deitado fora por `enviar()`. Estes testes fixam o novo
contrato: o canal guarda o motivo em `ultimo_resultado` e só repete falhas
transitórias.

Todos offline: `requests.post` do módulo é sempre substituído.
"""
from unittest import mock
from unittest.mock import patch

import pytest
import requests

from app.notifications.channels.telegram import (
    TelegramChannel,
    _ESPERA_ENTRE_TENTATIVAS,
    _STATUS_TRANSITORIOS,
)


class Utilizador:
    """Duplo mínimo — o canal só precisa do chat_id."""

    def __init__(self, chat_id='12345'):
        self.telegram_chat_id = chat_id


def _resposta(status, corpo):
    """Falsa resposta HTTP com o corpo que a Bot API devolveria."""
    resposta = mock.Mock()
    resposta.status_code = status
    if corpo is None:
        resposta.json.side_effect = ValueError('corpo vazio')
    else:
        resposta.json.return_value = corpo
    return resposta


def _sucesso(message_id=777):
    return _resposta(200, {'ok': True, 'result': {'message_id': message_id}})


def _insucesso(status, codigo, descricao):
    return _resposta(status, {'ok': False, 'error_code': codigo,
                              'description': descricao})


# ═════════ Sucesso ═════════

def test_sucesso_devolve_true_e_guarda_message_id():
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               return_value=_sucesso()) as pedido:
        assert canal.enviar(Utilizador(), 'Assunto', 'Corpo') is True
    assert canal.ultimo_resultado == {
        'sucesso': True, 'message_id': 777, 'erro': None}
    # O valor de retorno continua bool — chamadores antigos não mudam.
    assert pedido.call_count == 1


def test_html_continua_a_escapar_conteudo_do_utilizador():
    """Regressão do escape: o HTML do Telegram parte com <, & ou _ crus."""
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               return_value=_sucesso()) as pedido:
        canal.enviar(Utilizador(), 'Resumo <hoje> &',
                     'Título: A & B <C> _ *', parse_mode='HTML')
    payload = pedido.call_args.kwargs['json']
    assert payload['parse_mode'] == 'HTML'
    assert payload['text'] == ('<b>Resumo &lt;hoje&gt; &amp;</b>\n\n'
                               'Título: A &amp; B &lt;C&gt; _ *')


# ═════════ Motivo da falha ═════════

@pytest.mark.parametrize('status,codigo,descricao,trecho', [
    (403, 403, 'Forbidden: bot was blocked by the user', 'blocked by the user'),
    (400, 400, "Bad Request: chat not found", 'chat not found'),
    (401, 401, 'Unauthorized', 'Unauthorized'),
])
def test_falha_permanente_regista_codigo_e_descricao(status, codigo, descricao, trecho):
    """O motivo tem de chegar ao log — é isto que faltava em 14/10/2026."""
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               return_value=_insucesso(status, codigo, descricao)) as pedido:
        assert canal.enviar(Utilizador(), 'Assunto', 'Corpo') is False
    erro = canal.ultimo_resultado['erro']
    assert f'HTTP {codigo}' in erro
    assert trecho in erro
    # Falha permanente: uma só tentativa, sem insistir.
    assert pedido.call_count == 1


def test_description_no_topo_do_corpo_formato_da_bot_api():
    """A Bot API do Telegram devolve `description` no TOPO do corpo:

        {"ok": false, "error_code": 403, "description": "Forbidden: ..."}

    Ao contrário da OpenRouter, que a aninha em `error`. Ler só o aninhado
    perdia o motivo — foi o que os primeiros testes apanharam.
    """
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               return_value=_resposta(403, {
                   'ok': False, 'error_code': 403,
                   'description': 'Forbidden: bot was blocked by the user',
               })):
        assert canal.enviar(Utilizador(), 'Assunto', 'Corpo') is False
    assert canal.ultimo_resultado['erro'] == (
        'HTTP 403 — Forbidden: bot was blocked by the user')



def test_http_200_com_corpo_de_erro_e_falha():
    """Lição da v1.4.4 aplicada ao Telegram: 200 com `ok: false` não é sucesso."""
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               return_value=_resposta(200, {'ok': False, 'error_code': 429,
                                            'description': 'Too Many Requests'})):
        assert canal.enviar(Utilizador(), 'Assunto', 'Corpo') is False
    assert canal.ultimo_resultado['sucesso'] is False
    assert 'Too Many Requests' in canal.ultimo_resultado['erro']


def test_corpo_nao_json_assume_o_status_http():
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               return_value=_resposta(502, None)) as pedido:
        assert canal.enviar(Utilizador(), 'Assunto', 'Corpo') is False
    assert canal.ultimo_resultado['erro'] == 'HTTP 502'
    # 502 é transitório: repete.
    assert pedido.call_count == 2


def test_resposta_so_com_status_200_e_sucesso():
    """Duplos de teste antigos devolvem só o status — têm de continuar a passar."""
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               return_value=_resposta(200, None)):
        assert canal.enviar(Utilizador(), 'Assunto', 'Corpo') is True
    assert canal.ultimo_resultado['sucesso'] is True


def test_erro_de_rede_registado_e_com_retry():
    """Timeout/rede: exactamente o cenário da task das 07:00."""
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               side_effect=requests.RequestException('timed out')) as pedido, \
            patch('app.notifications.channels.telegram.time.sleep') as dormir:
        assert canal.enviar(Utilizador(), 'Assunto', 'Corpo') is False
    assert 'Erro de rede' in canal.ultimo_resultado['erro']
    assert 'timed out' in canal.ultimo_resultado['erro']
    assert pedido.call_count == 2
    dormir.assert_called_once_with(_ESPERA_ENTRE_TENTATIVAS)


def test_sem_chat_id_falha_sem_chamar_a_api():
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post') as pedido:
        assert canal.enviar(Utilizador(chat_id=None), 'Assunto', 'Corpo') is False
    assert canal.ultimo_resultado['erro'] == 'Destinatário sem chat_id de Telegram.'
    pedido.assert_not_called()


# ═════════ Retry ═════════

def test_falha_transitoria_repetida_ate_passar():
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               side_effect=[_resposta(503, None), _sucesso()]), \
            patch('app.notifications.channels.telegram.time.sleep'):
        assert canal.enviar(Utilizador(), 'Assunto', 'Corpo') is True
    assert canal.ultimo_resultado['sucesso'] is True
    assert canal.ultimo_resultado['message_id'] == 777


@pytest.mark.parametrize('status', sorted(_STATUS_TRANSITORIOS))
def test_status_transitorios_repetem(status):
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               return_value=_resposta(status, None)) as pedido, \
            patch('app.notifications.channels.telegram.time.sleep'):
        canal.enviar(Utilizador(), 'Assunto', 'Corpo')
    assert pedido.call_count == 2


@pytest.mark.parametrize('status', [400, 401, 403, 404, 409])
def test_status_permanentes_nao_repetem(status):
    canal = TelegramChannel('token')
    with patch('app.notifications.channels.telegram.requests.post',
               return_value=_resposta(status, None)) as pedido, \
            patch('app.notifications.channels.telegram.time.sleep') as dormir:
        canal.enviar(Utilizador(), 'Assunto', 'Corpo')
    assert pedido.call_count == 1
    dormir.assert_not_called()

