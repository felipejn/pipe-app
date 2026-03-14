import os
from app.notifications.channels.telegram import TelegramChannel
from app.notifications.channels.email import EmailChannel


class NotificationService:
    """Serviço central de notificações do PIPE.

    Cada módulo chama apenas notification_service.send() sem conhecer
    os canais de entrega. O serviço consulta as preferências do
    utilizador e despacha para os canais activos.

    Uso:
        from app.notifications import notification_service

        notification_service.send(
            user=current_user,
            type='resultado_euromilhoes',
            subject='Resultados de hoje',
            body='Verificámos os teus jogos...',
            data={'acertos': 3}
        )
    """

    def __init__(self):
        self._canais = {}
        self._inicializado = False

    def _inicializar_canais(self):
        """Inicializa os canais com as variáveis de ambiente.
        Chamado na primeira utilização (lazy init) para garantir
        que o contexto Flask já está disponível.
        """
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if telegram_token:
            self._canais['telegram'] = TelegramChannel(token=telegram_token)

        sendgrid_key = os.environ.get('SENDGRID_API_KEY')
        sendgrid_from = os.environ.get('SENDGRID_FROM_EMAIL')
        if sendgrid_key and sendgrid_from:
            self._canais['email'] = EmailChannel(
                api_key=sendgrid_key,
                remetente=sendgrid_from,
            )

        self._inicializado = True

    def send(self, user, type, subject, body, data=None):
        """Envia notificação ao utilizador pelos canais activos.

        Args:
            user:    instância de User (Flask-Login current_user)
            type:    identificador do tipo (ex: 'resultado_euromilhoes')
            subject: texto curto para assunto/título
            body:    corpo da mensagem
            data:    dict opcional com dados extra

        Returns:
            dict com resultado por canal, ex: {'telegram': True, 'email': False}
        """
        if not self._inicializado:
            self._inicializar_canais()

        prefs = getattr(user, 'notificacao_prefs', None)
        resultados = {}

        # Telegram
        canal_tg = self._canais.get('telegram')
        if canal_tg and prefs and prefs.telegram_activo:
            # Injecta o chat_id no objecto user para o canal poder aceder
            user.telegram_chat_id = prefs.telegram_chat_id
            resultados['telegram'] = canal_tg.enviar(user, subject, body, data)
        else:
            resultados['telegram'] = None  # não activo

        # Email
        canal_email = self._canais.get('email')
        if canal_email and prefs and prefs.email_activo:
            resultados['email'] = canal_email.enviar(user, subject, body, data)
        else:
            resultados['email'] = None  # não activo

        return resultados


# Instância global — importar directamente nos módulos
notification_service = NotificationService()
