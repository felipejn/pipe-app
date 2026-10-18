from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.settings import settings
from app.notifications.models import UserNotificationPreferences


@settings.route('/')
@login_required
def index():
    prefs = current_user.notificacao_prefs
    if not prefs:
        prefs = UserNotificationPreferences(user_id=current_user.id)
        db.session.add(prefs)
        db.session.commit()
    return render_template('settings/index.html', prefs=prefs)


@settings.route('/notificacoes', methods=['POST'])
@login_required
def guardar_notificacoes():
    prefs = current_user.notificacao_prefs
    if not prefs:
        prefs = UserNotificationPreferences(user_id=current_user.id)
        db.session.add(prefs)

    # Telegram
    telegram_chat_id = request.form.get('telegram_chat_id', '').strip()
    prefs.telegram_chat_id = telegram_chat_id or None
    prefs.telegram_activo = bool(telegram_chat_id) and \
        'telegram_activo' in request.form

    # Email
    prefs.email_activo = 'email_activo' in request.form

    # Tipos de notificação
    prefs.notificar_resultados = 'notificar_resultados' in request.form

    db.session.commit()
    flash('Definições guardadas com sucesso.', 'sucesso')
    return redirect(url_for('settings.index'))


@settings.route('/testar-telegram', methods=['POST'])
@login_required
def testar_telegram():
    """Envia mensagem de teste ao utilizador via Telegram."""
    from app.notifications.channels.telegram import TelegramChannel
    import os

    prefs = current_user.notificacao_prefs
    if not prefs or not prefs.telegram_chat_id:
        flash('Introduz primeiro o teu chat_id do Telegram.', 'erro')
        return redirect(url_for('settings.index'))

    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        flash('TELEGRAM_BOT_TOKEN não configurado no servidor.', 'erro')
        return redirect(url_for('settings.index'))

    canal = TelegramChannel(token=token)
    current_user.telegram_chat_id = prefs.telegram_chat_id
    sucesso = canal.enviar(
        current_user,
        'Teste PIPE',
        '✅ Notificações Telegram configuradas com sucesso!\n\nVais receber aqui as notificações do PIPE.',
    )

    if sucesso:
        flash('Mensagem de teste enviada com sucesso!', 'sucesso')
    else:
        # O canal guarda o motivo exacto (HTTP + description da Bot API).
        # Mostrá-lo evita o ciclo «erro genérico → tentar às cegas» — e o
        # conselho tem de depender do tipo de erro: mandar verificar o chat_id
        # num 401 (token) ou num erro de proxy é um beco sem saída.
        detalhe = (canal.ultimo_resultado or {}).get('erro') or 'motivo desconhecido'
        flash(f'Erro ao enviar: {detalhe} {_conselho_telegram(detalhe)}', 'erro')

    return redirect(url_for('settings.index'))


def _conselho_telegram(motivo):
    """Traduz o motivo da falha na acção concreta a tentar.

    Cada família de erro tem uma correcção diferente e nenhuma serve para as
    outras: token inválido → `.env` + Reload; bot bloqueado → o utilizador
    retomar a conversa; chat inexistente → corrigir o chat_id; proxy → é o
    servidor, não a configuração do utilizador.
    """
    texto = (motivo or '').lower()
    if '401' in texto or 'unauthorized' in texto:
        return ('Token inválido ou revogado — corrige TELEGRAM_BOT_TOKEN no .env '
                'do servidor e faz Reload.')
    if 'proxyerror' in texto or 'proxy' in texto or 'erro de rede' in texto:
        return ('Falha de rede do servidor (proxy) a contactar a API do Telegram '
                '— não é o chat_id.')
    if '403' in texto or 'blocked' in texto or 'bot was' in texto:
        return ('O bot não consegue iniciar a conversa — envia-lhe primeiro uma '
                'mensagem no Telegram e volta a testar.')
    if 'chat not found' in texto or 'chat_id' in texto or '400' in texto:
        return ('Confirma que o chat_id está correcto.')
    return 'Confirma a configuração do Telegram no servidor.'


@settings.route('/testar-email', methods=['POST'])
@login_required
def testar_email():
    """Envia email de teste ao utilizador via Zoho Mail."""
    from app.notifications.channels.email import EmailChannel
    prefs = current_user.notificacao_prefs
    if not prefs or not prefs.email_activo:
        flash('Activa primeiro o canal de email.', 'erro')
        return redirect(url_for('settings.index'))

    configuracao = {
        'client_id': current_app.config.get('ZOHO_CLIENT_ID'),
        'client_secret': current_app.config.get('ZOHO_CLIENT_SECRET'),
        'refresh_token': current_app.config.get('ZOHO_REFRESH_TOKEN'),
        'account_id': current_app.config.get('ZOHO_ACCOUNT_ID'),
        'remetente': current_app.config.get('ZOHO_FROM_EMAIL'),
        'dc': current_app.config.get('ZOHO_DC', 'eu'),
    }

    if not all(configuracao.values()):
        flash('As variáveis ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN, ZOHO_ACCOUNT_ID e ZOHO_FROM_EMAIL têm de estar configuradas.', 'erro')
        return redirect(url_for('settings.index'))

    try:
        canal = EmailChannel(**configuracao)
        sucesso = canal.enviar_template(current_user, 'teste', {
            'nome': current_user.nome_apresentacao,
        })
    except Exception as erro:
        current_app.logger.error(
            'Falha inesperada no teste de email Zoho: %s', type(erro).__name__)
        flash('O teste de email falhou antes de concluir o envio. '
              'Consulta o registo da aplicação para o diagnóstico.', 'erro')
        return redirect(url_for('settings.index'))

    if sucesso:
        flash(f'Email de teste enviado para {current_user.email}.', 'sucesso')
    else:
        detalhe = (canal.ultimo_resultado or {}).get('erro')
        if detalhe:
            flash(f'Erro ao enviar pelo Zoho Mail ({detalhe}).', 'erro')
        else:
            flash('Erro ao enviar. Confirma a configuração do Zoho Mail no servidor.', 'erro')

    return redirect(url_for('settings.index'))
