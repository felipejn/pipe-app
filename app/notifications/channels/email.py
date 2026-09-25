import base64
import datetime

import requests
from app.notifications.channels.base import BaseChannel


class EmailChannel(BaseChannel):
    """Canal de notificação via email (Mailjet)."""

    API_URL = 'https://api.mailjet.com/v3.1/send'
    API_URL_V3 = 'https://api.mailjet.com/v3'  # consulta de actividade

    def __init__(self, api_key, api_secret, remetente):
        """
        Args:
            api_key:     chave API Mailjet (variável de ambiente MAILJET_API_KEY)
            api_secret:  API secret Mailjet (variável de ambiente MAILJET_API_SECRET)
            remetente:   endereço de email do remetente (ex: 'pipe@example.com')
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.remetente = remetente
        # Resultado do último `enviar()`: o bool devolvido não chega para
        # diagnosticar — aqui fica o ID da mensagem no Mailjet (guardado depois
        # no convite, para se poder verificar a entrega real) e o motivo da falha.
        self.ultimo_resultado = {'sucesso': False, 'message_id': None, 'erro': None}

    def _cabecalhos(self):
        """Autenticação Basic Mailjet (API Key:API Secret)."""
        credentials = f'{self.api_key}:{self.api_secret}'
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/json',
        }

    def enviar(self, utilizador, assunto, corpo, dados=None):
        """Envia email ao utilizador via Mailjet.

        Requer que utilizador.email esteja preenchido.
        Actualiza `self.ultimo_resultado` com o MessageID (sucesso) ou o motivo
        da falha — o valor de retorno continua a ser bool, por compatibilidade
        com os restantes chamadores (2FA, recuperação de password, testes).
        """
        if not self.esta_configurado(utilizador):
            self.ultimo_resultado = {
                'sucesso': False, 'message_id': None,
                'erro': 'Destinatário sem email.',
            }
            return False

        try:
            resposta = requests.post(
                self.API_URL,
                headers=self._cabecalhos(),
                json={
                    'Messages': [
                        {
                            'From': {'Email': self.remetente},
                            'To': [{'Email': utilizador.email}],
                            'Subject': assunto,
                            'TextPart': corpo,
                        }
                    ]
                },
                timeout=10,
            )
            # Mailjet devolve 200 em caso de sucesso
            if resposta.status_code == 200:
                # Verifica se houve erros individuais no corpo da resposta
                try:
                    resultado = resposta.json()
                    messages = resultado.get('Messages', [])
                    if messages and messages[0].get('Status') == 'success':
                        # O ID da mensagem vem em Messages[0].To[0].MessageID —
                        # é ele que permite depois verificar a entrega real.
                        destinatarios = messages[0].get('To') or []
                        message_id = destinatarios[0].get('MessageID') if destinatarios else None
                        self.ultimo_resultado = {
                            'sucesso': True, 'message_id': message_id, 'erro': None,
                        }
                        return True
                    primeiro = messages[0] if messages else {}
                    detalhe = (primeiro.get('ErrorMessage')
                               or primeiro.get('Status')
                               or 'resposta vazia')
                    self.ultimo_resultado = {
                        'sucesso': False, 'message_id': None,
                        'erro': f'Mailjet: {detalhe}',
                    }
                    return False
                except (ValueError, KeyError, IndexError):
                    self.ultimo_resultado = {
                        'sucesso': False, 'message_id': None,
                        'erro': 'Resposta inválida do Mailjet.',
                    }
                    return False
            self.ultimo_resultado = {
                'sucesso': False, 'message_id': None,
                'erro': f'HTTP {resposta.status_code}',
            }
            return False
        except requests.RequestException as e:
            self.ultimo_resultado = {
                'sucesso': False, 'message_id': None,
                'erro': f'Erro de rede: {e}',
            }
            return False

    def consultar_estado(self, message_id):
        """Consulta a actividade Mailjet de uma mensagem já enviada.

        Aceitar o pedido (200 + success) não prova que o email chegou — pode
        depois ser entregue, rejeitado ou parar em spam. Este método devolve o
        estado real, o histórico de eventos e o motivo de qualquer falha (ex.:
        o `550 5.7.40` do Gmail quando o domínio remetente não está autenticado).

        Returns:
            dict com `estado` (último estado conhecido: 'sent', 'delivered',
            'softbounced', ...), `eventos` ([{'quando', 'tipo'}] cronológicos),
            `motivo` (comentário do Mailjet — texto do bounce — ou None) e
            `erro` (None, ou mensagem de falha da própria consulta).
        """
        vazio = {'estado': None, 'eventos': [], 'motivo': None, 'erro': None}
        try:
            # 1 — histórico de eventos (sent, delivered, bounced, opened, ...)
            r_hist = requests.get(
                f'{self.API_URL_V3}/REST/messagehistory/{message_id}',
                headers=self._cabecalhos(), timeout=15,
            )
            if r_hist.status_code != 200:
                vazio['erro'] = f'HTTP {r_hist.status_code}'
                return vazio

            brutos = sorted(r_hist.json().get('Data', []),
                            key=lambda e: int(e.get('EventAt') or 0))
            eventos, motivo = [], None
            for e in brutos:
                eventos.append({'quando': self._formatar_tempo(e.get('EventAt')),
                                'tipo': e.get('EventType', '?')})
                if e.get('Comment'):
                    motivo = e['Comment']  # falha mais recente = motivo actual

            estado = eventos[-1]['tipo'] if eventos else None

            # 2 — estado oficial da mensagem (o histórico pode estar vazio
            #     logo após o envio)
            r_msg = requests.get(
                f'{self.API_URL_V3}/REST/message/{message_id}',
                headers=self._cabecalhos(), timeout=15,
            )
            if r_msg.status_code == 200:
                dados = r_msg.json().get('Data') or []
                if dados and dados[0].get('Status'):
                    estado = dados[0]['Status']

            return {'estado': estado, 'eventos': eventos,
                    'motivo': motivo, 'erro': None}
        except requests.RequestException as e:
            vazio['erro'] = f'Erro de rede: {e}'
            return vazio
        except (ValueError, KeyError, IndexError, TypeError, OSError) as e:
            vazio['erro'] = f'Reposta inválida do Mailjet: {e}'
            return vazio

    @staticmethod
    def _formatar_tempo(timestamp):
        """Timestamp Unix do Mailjet → 'dd/mm/aaaa hh:mm' (hora local)."""
        try:
            return datetime.datetime.fromtimestamp(int(timestamp)).strftime('%d/%m/%Y %H:%M')
        except (TypeError, ValueError, OSError):
            return '?'

    def esta_configurado(self, utilizador):
        """Retorna True se o utilizador tem email preenchido."""
        return bool(getattr(utilizador, 'email', None))
