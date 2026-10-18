import json
import logging
import os
import tempfile
import time

import requests
from flask import current_app, has_app_context

from app.notifications.channels.base import BaseChannel


class EmailChannel(BaseChannel):
    """Canal de notificações por email através da API Zoho Mail."""

    TIMEOUT = 10
    MARGEM_EXPIRACAO = 300
    _TOKEN_INVALIDO_CODES = {'401', 'INVALID_OAUTHTOKEN', 'INVALID_TOKEN'}

    def __init__(self, client_id=None, client_secret=None, refresh_token=None,
                 account_id=None, remetente=None, dc='eu', cache_path=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.account_id = account_id
        self.remetente = remetente
        self.dc = (dc or 'eu').strip().lower()
        self.accounts_url = f'https://accounts.zoho.{self.dc}/oauth/v2/token'
        self.mail_url = f'https://mail.zoho.{self.dc}/api/accounts/{account_id}/messages'
        self.cache_path = cache_path or self._caminho_cache()
        self._ultimo_erro = None
        self.ultimo_resultado = {'sucesso': False, 'message_id': None, 'erro': None}

    @staticmethod
    def _caminho_cache():
        if has_app_context():
            configurado = current_app.config.get('ZOHO_TOKEN_CACHE_PATH')
            if configurado:
                return configurado
            pasta = current_app.instance_path
        else:
            pasta = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'instance'))
        return os.path.join(pasta, 'zoho_access_token.json')

    def _configurado(self):
        return all((self.client_id, self.client_secret, self.refresh_token,
                    self.account_id, self.remetente))

    def _ler_cache(self):
        try:
            with open(self.cache_path, encoding='utf-8') as ficheiro:
                cache = json.load(ficheiro)
            if (cache.get('access_token') and
                    float(cache.get('expires_at', 0)) - time.time() > self.MARGEM_EXPIRACAO):
                return cache['access_token']
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return None

    def _guardar_cache(self, token, expires_in):
        cache = {'access_token': token,
                 'expires_at': time.time() + max(0, int(expires_in))}
        temporario = None
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with tempfile.NamedTemporaryFile('w', encoding='utf-8',
                                             dir=os.path.dirname(self.cache_path),
                                             delete=False) as ficheiro:
                temporario = ficheiro.name
                json.dump(cache, ficheiro)
            os.replace(temporario, self.cache_path)
        except (OSError, ValueError, TypeError):
            if temporario:
                try:
                    os.unlink(temporario)
                except OSError:
                    pass

    def _invalidar_cache(self):
        try:
            os.unlink(self.cache_path)
        except OSError:
            pass

    def _obter_access_token(self, renovar=False):
        if not renovar:
            token = self._ler_cache()
            if token:
                return token
        try:
            resposta = requests.post(
                self.accounts_url,
                data={
                    'grant_type': 'refresh_token',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'refresh_token': self.refresh_token,
                }, timeout=self.TIMEOUT,
            )
            if resposta.status_code != 200:
                detalhe = self._resumo_resposta(
                    self._json_seguro(resposta),
                    (self.client_id, self.client_secret, self.refresh_token),
                )
                self._erro('renovação do token',
                           f'HTTP {resposta.status_code}; {detalhe}')
                return None
            dados = resposta.json()
            token = dados.get('access_token')
            if not token or dados.get('error'):
                detalhe = self._resumo_resposta(
                    dados, (self.client_id, self.client_secret,
                            self.refresh_token, token),
                )
                self._erro('renovação do token',
                           detalhe or 'resposta sem token válido')
                return None
            self._guardar_cache(token, dados.get('expires_in', 3600))
            return token
        except Exception as erro:
            self._erro('renovação do token', type(erro).__name__)
            return None

    def _erro(self, operacao, detalhe):
        self._ultimo_erro = f'{operacao}: {detalhe}'
        logging.error('[Email Zoho] Falha na %s: %s', operacao, detalhe)

    @staticmethod
    def _json_seguro(resposta):
        try:
            dados = resposta.json()
        except (ValueError, TypeError, AttributeError):
            return {}
        return dados if isinstance(dados, dict) else {}

    @staticmethod
    def _resumo_resposta(dados, sensiveis=()):
        """Extrai detalhes úteis da resposta, removendo dados do pedido."""
        if not isinstance(dados, dict):
            return ''
        status = dados.get('status')
        status = status if isinstance(status, dict) else {}
        data = dados.get('data')
        data = data if isinstance(data, dict) else {}
        campos = (
            ('status.code', status.get('code')),
            ('status.description', status.get('description')),
            ('message', dados.get('message')),
            ('error', dados.get('error')),
            ('data.moreInfo', data.get('moreInfo')),
            ('data.message', data.get('message')),
            ('data.error', data.get('error')),
        )
        partes = []
        for nome, valor in campos:
            if isinstance(valor, (str, int, float)) and str(valor).strip():
                partes.append(f'{nome}={str(valor).strip()}')
        resumo = ' | '.join(partes)
        for sensivel in sensiveis:
            if isinstance(sensivel, str) and len(sensivel) >= 3:
                resumo = resumo.replace(sensivel, '[REDACTADO]')
        resumo = ' '.join(resumo.split())
        return resumo[:300]

    @classmethod
    def _token_invalido(cls, resposta, dados):
        status = dados.get('status') if isinstance(dados, dict) else {}
        if not isinstance(status, dict):
            status = {}
        codigo = str(status.get('code', '')).upper()
        erro = str(dados.get('error', '')).upper()
        return resposta.status_code == 401 or codigo in cls._TOKEN_INVALIDO_CODES or erro in cls._TOKEN_INVALIDO_CODES

    def _enviar_pedido(self, token, utilizador, assunto, corpo, html):
        return requests.post(
            self.mail_url,
            headers={'Authorization': f'Zoho-oauthtoken {token}',
                     'Accept': 'application/json',
                     'Content-Type': 'application/json'},
            json={
                'fromAddress': self.remetente,
                'toAddress': utilizador.email,
                'subject': assunto,
                'content': html if html else corpo,
                'mailFormat': 'html' if html else 'plaintext',
            }, timeout=self.TIMEOUT,
        )

    def enviar(self, utilizador, assunto, corpo, dados=None, html=None):
        """Envia uma mensagem e devolve booleano, mantendo o contrato existente."""
        self._ultimo_erro = None
        if not self.esta_configurado(utilizador):
            self.ultimo_resultado = {'sucesso': False, 'message_id': None,
                                     'erro': 'Canal Zoho não configurado ou destinatário sem email.'}
            return False

        token = self._obter_access_token()
        if not token:
            self.ultimo_resultado = {'sucesso': False, 'message_id': None,
                                     'erro': self._ultimo_erro or 'Não foi possível obter o token de acesso.'}
            return False

        for tentativa in range(2):
            try:
                resposta = self._enviar_pedido(token, utilizador, assunto, corpo, html)
                try:
                    dados_resposta = resposta.json()
                    if not isinstance(dados_resposta, dict):
                        dados_resposta = {}
                except (ValueError, TypeError):
                    dados_resposta = {}
                    if self._token_invalido(resposta, dados_resposta) and tentativa == 0:
                        self._invalidar_cache()
                        token = self._obter_access_token(renovar=True)
                        if token:
                            continue
                    self._erro('envio', 'JSON inválido na resposta')
                    break

                if self._token_invalido(resposta, dados_resposta) and tentativa == 0:
                    self._invalidar_cache()
                    token = self._obter_access_token(renovar=True)
                    if token:
                        continue
                status = dados_resposta.get('status') or {}
                if resposta.status_code == 200 and str(status.get('code')) == '200':
                    dados_envio = dados_resposta.get('data') or {}
                    message_id = dados_envio.get('messageId') if isinstance(dados_envio, dict) else None
                    self.ultimo_resultado = {'sucesso': True, 'message_id': message_id, 'erro': None}
                    self._ultimo_erro = None
                    return True
                detalhe = self._resumo_resposta(
                    dados_resposta,
                    (self.client_id, self.client_secret, self.refresh_token,
                     token, getattr(utilizador, 'email', None), assunto,
                     corpo, html),
                )
                if not detalhe:
                    codigo = str(status.get('code', ''))
                    codigo_seguro = codigo if codigo.isdigit() else 'não numérico'
                    detalhe = f'código Zoho {codigo_seguro}'
                self._erro('envio', f'HTTP {resposta.status_code}; {detalhe}')
                break
            except Exception as erro:
                self._erro('envio', type(erro).__name__)
                break

        self.ultimo_resultado = {'sucesso': False, 'message_id': None,
                                 'erro': self._ultimo_erro or 'Falha no envio através do Zoho Mail.'}
        return False

    def enviar_template(self, utilizador, tipo, contexto):
        """Compõe e envia uma mensagem PIPE em HTML ou texto simples."""
        from app.notifications.email_templates import compor_email

        assunto, texto, html = compor_email(tipo, contexto)
        return self.enviar(utilizador, assunto, texto, html=html)

    def esta_configurado(self, utilizador):
        return bool(self._configurado() and getattr(utilizador, 'email', None))
