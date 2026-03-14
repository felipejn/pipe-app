import requests
from app.notifications.channels.base import BaseChannel


class TelegramChannel(BaseChannel):
    """Canal de notificação via Telegram Bot API."""

    API_URL = 'https://api.telegram.org/bot{token}/sendMessage'

    def __init__(self, token):
        """
        Args:
            token: token do bot Telegram (variável de ambiente TELEGRAM_BOT_TOKEN)
        """
        self.token = token

    def enviar(self, utilizador, assunto, corpo, dados=None):
        """Envia mensagem Telegram ao utilizador.

        Requer que utilizador.telegram_chat_id esteja preenchido.
        """
        if not self.esta_configurado(utilizador):
            return False

        texto = f'*{assunto}*\n\n{corpo}'

        try:
            resposta = requests.post(
                self.API_URL.format(token=self.token),
                json={
                    'chat_id': utilizador.telegram_chat_id,
                    'text': texto,
                    'parse_mode': 'Markdown',
                },
                timeout=10,
            )
            return resposta.status_code == 200
        except requests.RequestException:
            return False

    def esta_configurado(self, utilizador):
        """Retorna True se o utilizador tem chat_id Telegram configurado."""
        return bool(getattr(utilizador, 'telegram_chat_id', None))
