from flask import render_template, redirect, url_for, flash, request
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
    from app.notifications import notification_service

    prefs = current_user.notificacao_prefs
    if not prefs or not prefs.telegram_chat_id:
        flash('Introduz primeiro o teu chat_id do Telegram.', 'erro')
        return redirect(url_for('settings.index'))

    # Activa temporariamente para o teste mesmo que o toggle esteja off
    current_user.telegram_chat_id = prefs.telegram_chat_id
    resultado = notification_service.send(
        user=current_user,
        type='teste',
        subject='Teste PIPE',
        body='✅ Notificações Telegram configuradas com sucesso!',
    )

    # Para o teste forçamos o envio directamente pelo canal
    from app.notifications.channels.telegram import TelegramChannel
    import os
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if token:
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
            flash('Erro ao enviar. Confirma que o chat_id está correcto e que enviaste uma mensagem ao bot primeiro.', 'erro')
    else:
        flash('TELEGRAM_BOT_TOKEN não configurado no servidor.', 'erro')

    return redirect(url_for('settings.index'))
