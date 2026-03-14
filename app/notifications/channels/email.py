import requests
from app.notifications.channels.base import BaseChannel


class EmailChannel(BaseChannel):
    """Canal de notificação via email (SendGrid)."""

    API_URL = 'https://api.sendgrid.com/v3/mail/send'

    def __init__(self, api_key, remetente):
        """
        Args:
            api_key:    chave API SendGrid (variável de ambiente SENDGRID_API_KEY)
            remetente:  endereço de email do remetente (ex: 'pipe@example.com')
        """
        self.api_key = api_key
        self.remetente = remetente

    def enviar(self, utilizador, assunto, corpo, dados=None):
        """Envia email ao utilizador via SendGrid.

        Requer que utilizador.email esteja preenchido.
        """
        if not self.esta_configurado(utilizador):
            return False

        try:
            resposta = requests.post(
                self.API_URL,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'personalizations': [
                        {
                            'to': [{'email': utilizador.email}],
                            'subject': assunto,
                        }
                    ],
                    'from': {'email': self.remetente},
                    'content': [
                        {'type': 'text/plain', 'value': corpo}
                    ],
                },
                timeout=10,
            )
            # SendGrid devolve 202 em caso de sucesso
            return resposta.status_code == 202
        except requests.RequestException:
            return False

    def esta_configurado(self, utilizador):
        """Retorna True se o utilizador tem email preenchido."""
        return bool(getattr(utilizador, 'email', None))
