import logging
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

        zoho_client_id = os.environ.get('ZOHO_CLIENT_ID')
        zoho_client_secret = os.environ.get('ZOHO_CLIENT_SECRET')
        zoho_refresh_token = os.environ.get('ZOHO_REFRESH_TOKEN')
        zoho_account_id = os.environ.get('ZOHO_ACCOUNT_ID')
        zoho_from = os.environ.get('ZOHO_FROM_EMAIL')
        if all((zoho_client_id, zoho_client_secret, zoho_refresh_token,
                zoho_account_id, zoho_from)):
            self._canais['email'] = EmailChannel(
                client_id=zoho_client_id,
                client_secret=zoho_client_secret,
                refresh_token=zoho_refresh_token,
                account_id=zoho_account_id,
                remetente=zoho_from,
                dc=os.environ.get('ZOHO_DC', 'eu'),
            )

        self._inicializado = True

    def send(self, user, type, subject, body, data=None, force_channel=None,
             telegram_parse_mode=None, email_template=None, email_context=None,
             telegram_include_subject=True):
        """Envia notificação ao utilizador pelos canais activos.

        Args:
            user:    instância de User (Flask-Login current_user)
            type:    identificador do tipo (ex: 'resultado_euromilhoes')
            subject: texto curto para assunto/título
            body:    corpo da mensagem
            data:    dict opcional com dados extra
            force_channel: envia apenas por este canal; actualmente suporta
                           'telegram' para acções manuais explícitas.
            telegram_parse_mode: modo de parsing opcional só para Telegram.

        Returns:
            dict com resultado por canal, ex: {'telegram': True, 'email': False}
        """
        if not self._inicializado:
            self._inicializar_canais()

        prefs = getattr(user, 'notificacao_prefs', None)
        resultados = {}

        if force_channel is not None:
            if force_channel != 'telegram':
                raise ValueError('Canal forçado desconhecido.')
            canal_tg = self._canais.get('telegram')
            if canal_tg and prefs and prefs.telegram_chat_id:
                user.telegram_chat_id = prefs.telegram_chat_id
                if telegram_parse_mode:
                    resultados['telegram'] = canal_tg.enviar(
                        user, subject, body, data,
                        parse_mode=telegram_parse_mode,
                        incluir_assunto=telegram_include_subject)
                else:
                    resultados['telegram'] = canal_tg.enviar(
                        user, subject, body, data,
                        incluir_assunto=telegram_include_subject)
            else:
                resultados['telegram'] = None
            self._registar_falhas(user, resultados)
            # Um canal forçado é exclusivo; não despacha por email.
            resultados['email'] = None
            return resultados

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
            if email_template:
                resultados['email'] = canal_email.enviar_template(
                    user, email_template, email_context or data or {})
            else:
                resultados['email'] = canal_email.enviar(user, subject, body, data)
        else:
            resultados['email'] = None  # não activo

        self._registar_falhas(user, resultados)
        return resultados

    def _registar_falhas(self, user, resultados):
        """Regista no log o motivo dos canais que falharam de facto.

        `False` e `None` não são a mesma coisa: `None` é canal não activo ou
        destinatário sem contacto (cenário esperado, silencioso), `False` é o
        canal a correr e a falhar — é esse que precisa de motivo no log.
        """
        for canal, valor in resultados.items():
            if valor is not False:
                continue
            motivo = self.ultimo_erro(canal) or 'motivo não detalhado'
            logging.error(
                '[Notificações] %s falhou para %s: %s',
                canal, getattr(user, 'username', user), motivo)

    def ultimo_erro(self, canal='telegram'):
        """Devolve o motivo legível da última falha de um canal.

        O canal guarda-o em `ultimo_resultado` (mesmo contrato do email, que
        já expunha `message_id`/`erro` para o /admin). Devolve None quando o
        canal não está inicializado ou não registou falha.
        """
        instancia = self._canais.get(canal)
        resultado = getattr(instancia, 'ultimo_resultado', None)
        if not resultado:
            return None
        return resultado.get('erro')


# Instância global — importar directamente nos módulos
notification_service = NotificationService()
