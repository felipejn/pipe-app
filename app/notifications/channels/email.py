import base64
import requests
from app.notifications.channels.base import BaseChannel


class EmailChannel(BaseChannel):
    """Canal de notificação via email (Mailjet)."""

    API_URL = 'https://api.mailjet.com/v3.1/send'

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

    def enviar(self, utilizador, assunto, corpo, dados=None):
        """Envia email ao utilizador via Mailjet.

        Requer que utilizador.email esteja preenchido.
        """
        if not self.esta_configurado(utilizador):
            return False

        try:
            # Mailjet usa autenticação Basic com API Key:API Secret
            credentials = f'{self.api_key}:{self.api_secret}'
            encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

            resposta = requests.post(
                self.API_URL,
                headers={
                    'Authorization': f'Basic {encoded}',
                    'Content-Type': 'application/json',
                },
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
                        return True
                    return False
                except (ValueError, KeyError):
                    return False
            return False
        except requests.RequestException:
            return False

    def esta_configurado(self, utilizador):
        """Retorna True se o utilizador tem email preenchido."""
        return bool(getattr(utilizador, 'email', None))
