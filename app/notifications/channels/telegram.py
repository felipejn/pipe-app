import html
import logging
import time

import requests
from app.notifications.channels.base import BaseChannel

logger = logging.getLogger(__name__)

# Falhas transitórias merecem uma segunda tentativa: a scheduled task corre
# sozinha às 07:00 e, sem retry, um timeout de rede deixava o dia inteiro sem
# resumo (e sem avisos de tarefas) — foi o que aconteceu em 14/10/2026, com
# `telegram=False` no log da task e o envio manual a funcionar minutos depois.
# Os 4xx permanentes (401 token inválido, 403 bot bloqueado, 400 entidade
# inválida) NÃO repetem: insistir só gasta tempo e disfarça a causa real.
_TENTATIVAS_TRANSITORIAS = 2
_ESPERA_ENTRE_TENTATIVAS = 2.0
_STATUS_TRANSITORIOS = {408, 425, 429, 500, 502, 503, 504}


class TelegramChannel(BaseChannel):
    """Canal de notificação via Telegram Bot API."""

    API_URL = 'https://api.telegram.org/bot{token}/sendMessage'
    TIMEOUT = 10

    def __init__(self, token):
        """
        Args:
            token: token do bot Telegram (variável de ambiente TELEGRAM_BOT_TOKEN)
        """
        self.token = token
        # O bool devolvido por `enviar()` não chega para diagnosticar: um
        # `False` tanto serve para «sem chat_id» como para «a API rejeitou» ou
        # «a rede falhou», indistinguíveis no log. Aqui fica o motivo exacto
        # (mesmo contrato do `EmailChannel.ultimo_resultado`); o valor de
        # retorno continua bool, por compatibilidade com os restantes
        # chamadores (2FA, settings, resumo diário, testes).
        self.ultimo_resultado = {'sucesso': False, 'message_id': None, 'erro': None}

    def _compor_texto(self, assunto, corpo, parse_mode):
        """Monta o texto final; em HTML escapa o conteúdo não confiável."""
        if parse_mode == 'HTML':
            # Chamadas HTML são para conteúdo não confiável: escapar título e
            # corpo impede que <, &, * ou _ estraguem o parsing do Telegram.
            return f'<b>{html.escape(str(assunto))}</b>\n\n{html.escape(str(corpo))}'
        return f'*{assunto}*\n\n{corpo}'

    def _enviar_uma_vez(self, chat_id, texto, parse_mode):
        """Faz um pedido sendMessage e devolve o resultado classificado.

        Returns:
            dict com `sucesso`, `message_id`, `erro` (legível) e `transitorio`
            (True se vale a pena repetir: rede, 5xx ou 429).
        """
        try:
            resposta = requests.post(
                self.API_URL.format(token=self.token),
                json={
                    'chat_id': chat_id,
                    'text': texto,
                    'parse_mode': parse_mode,
                },
                timeout=self.TIMEOUT,
            )
        except requests.RequestException as erro:
            return {'sucesso': False, 'message_id': None,
                    'erro': f'Erro de rede: {erro}', 'transitorio': True}

        status = getattr(resposta, 'status_code', 0)
        try:
            dados = resposta.json()
        except (AttributeError, TypeError, ValueError):
            # Corpo ausente, vazio ou não-JSON: o status HTTP decide.
            dados = None

        # O Telegram responde sempre com {"ok": true|false, ...}. Quando o
        # corpo não é legível (ou não tem `ok`), o status HTTP é a única
        # autoridade — é o caso dos duplos de teste que devolvem só o status.
        ok = dados.get('ok') if isinstance(dados, dict) else None
        if ok is None:
            if status == 200:
                return {'sucesso': True, 'message_id': None,
                        'erro': None, 'transitorio': False}
            return {'sucesso': False, 'message_id': None,
                    'erro': f'HTTP {status}',
                    'transitorio': status in _STATUS_TRANSITORIOS}

        if ok is True:
            message_id = None
            if isinstance(dados.get('result'), dict):
                message_id = dados['result'].get('message_id')
            return {'sucesso': True, 'message_id': message_id,
                    'erro': None, 'transitorio': False}

        # `ok: false` — o corpo diz porque falhou. Atenção: a Bot API do Telegram
        # coloca `description` NO TOPO do corpo, ao contrário da OpenRouter, que
        # a aninha em `error`; aceitam-se as duas formas.
        descricao = dados.get('description')
        if not descricao:
            erro = dados.get('error')
            if isinstance(erro, dict):
                descricao = erro.get('description') or erro.get('message')
            elif erro:
                descricao = str(erro)
        codigo = dados.get('error_code') or status
        descricao = str(descricao or 'motivo não indicado').strip()[:200]
        return {'sucesso': False, 'message_id': None,
                'erro': f'HTTP {codigo} — {descricao}',
                'transitorio': status in _STATUS_TRANSITORIOS}

    def enviar(self, utilizador, assunto, corpo, dados=None, parse_mode='Markdown'):
        """Envia mensagem Telegram ao utilizador.

        Requer que utilizador.telegram_chat_id esteja preenchido. Guarda o
        motivo de qualquer falha em `self.ultimo_resultado`.
        """
        if not self.esta_configurado(utilizador):
            self.ultimo_resultado = {
                'sucesso': False, 'message_id': None,
                'erro': 'Destinatário sem chat_id de Telegram.',
            }
            return False

        texto = self._compor_texto(assunto, corpo, parse_mode)
        chat_id = utilizador.telegram_chat_id

        resultado = self._enviar_uma_vez(chat_id, texto, parse_mode)
        for tentativa in range(2, _TENTATIVAS_TRANSITORIAS + 1):
            if resultado['sucesso'] or not resultado['transitorio']:
                break
            time.sleep(_ESPERA_ENTRE_TENTATIVAS)
            resultado = self._enviar_uma_vez(chat_id, texto, parse_mode)

        self.ultimo_resultado = {
            'sucesso': resultado['sucesso'],
            'message_id': resultado['message_id'],
            'erro': resultado['erro'],
        }
        if not resultado['sucesso']:
            logger.error('[Telegram] Envio falhou: %s', resultado['erro'])
        return resultado['sucesso']

    def esta_configurado(self, utilizador):
        """Retorna True se o utilizador tem chat_id Telegram configurado."""
        return bool(getattr(utilizador, 'telegram_chat_id', None))
