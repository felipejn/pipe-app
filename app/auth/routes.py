import random
import os
from datetime import datetime, timedelta

from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.auth import auth
from app.auth.forms import (
    LoginForm, RegistoForm, AlterarPasswordForm,
    VerificarCodigoForm, ConfigurarDoisFAForm
)
from app.auth.models import User
from app.notifications.channels.telegram import TelegramChannel
from app.notifications.channels.email import EmailChannel
from flask import current_app


# ── Helpers de envio ───────────────────────────────────────────────────────

def _gerar_e_guardar_codigo(user):
    """Gera código de 6 dígitos e guarda na BD. Não envia."""
    codigo = str(random.randint(100000, 999999))
    user.dois_fa_codigo = codigo
    user.dois_fa_expira = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    return codigo


def _enviar_codigo_telegram(user):
    """Envia o código 2FA via Telegram. Retorna True se bem-sucedido."""
    codigo = _gerar_e_guardar_codigo(user)
    token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    canal = TelegramChannel(token=token)

    class _Destinatario:
        telegram_chat_id = user.dois_fa_chat_id

    return canal.enviar(
        utilizador=_Destinatario(),
        assunto='Código de acesso PIPE',
        corpo=f'O teu código de verificação é: *{codigo}*\n\nExpira em 10 minutos.',
    )


def _enviar_codigo_email(user):
    """Envia o código 2FA via email. Retorna True se bem-sucedido."""
    codigo = _gerar_e_guardar_codigo(user)
    api_key = current_app.config.get('SENDGRID_API_KEY')
    remetente = current_app.config.get('SENDGRID_FROM_EMAIL')
    canal = EmailChannel(api_key=api_key, remetente=remetente)

    return canal.enviar(
        user,
        assunto='Código de acesso PIPE',
        corpo=f'O teu código de verificação é: {codigo}\n\nExpira em 10 minutos.',
    )


# ── Login ──────────────────────────────────────────────────────────────────

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.activo and user.check_password(form.password.data):

            metodos = user.metodos_2fa_activos()

            if len(metodos) == 0:
                # Sem 2FA — login directo
                login_user(user, remember=form.lembrar.data)
                user.ultimo_login = datetime.utcnow()
                db.session.commit()
                proximo = request.args.get('next')
                return redirect(proximo or url_for('dashboard'))

            # Guarda estado na sessão
            session['2fa_user_id'] = user.id
            session['2fa_lembrar'] = form.lembrar.data

            if len(metodos) == 1:
                # Só um método — envia imediatamente
                return redirect(url_for('auth.enviar_2fa', metodo=metodos[0]))

            # Vários métodos — deixa o utilizador escolher
            return redirect(url_for('auth.escolher_2fa'))

        flash('Utilizador ou palavra-passe incorrectos.', 'erro')

    return render_template('auth/login.html', form=form)


# ── Escolher método 2FA ────────────────────────────────────────────────────

@auth.route('/2fa/escolher')
def escolher_2fa():
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.pop('2fa_user_id', None)
        return redirect(url_for('auth.login'))

    metodos = user.metodos_2fa_activos()
    return render_template('auth/escolher_2fa.html', metodos=metodos)


# ── Enviar código pelo método escolhido ───────────────────────────────────

@auth.route('/2fa/enviar/<metodo>')
def enviar_2fa(metodo):
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user or metodo not in user.metodos_2fa_activos():
        return redirect(url_for('auth.login'))

    session['2fa_metodo'] = metodo

    if metodo == 'telegram':
        enviado = _enviar_codigo_telegram(user)
        destino = 'Telegram'
    else:
        enviado = _enviar_codigo_email(user)
        destino = f'email ({user.email})'

    if enviado:
        flash(f'Código enviado para o teu {destino}.', 'info')
    else:
        flash(f'Erro ao enviar código para {destino}. Tenta novamente.', 'erro')
        return redirect(url_for('auth.escolher_2fa') if len(user.metodos_2fa_activos()) > 1
                        else url_for('auth.login'))

    return redirect(url_for('auth.verificar_2fa'))


# ── Verificação 2FA ────────────────────────────────────────────────────────

@auth.route('/2fa/verificar', methods=['GET', 'POST'])
def verificar_2fa():
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.pop('2fa_user_id', None)
        return redirect(url_for('auth.login'))

    metodo = session.get('2fa_metodo', 'telegram')
    form = VerificarCodigoForm()

    if form.validate_on_submit():
        if user.codigo_valido(form.codigo.data):
            user.limpar_codigo()
            user.ultimo_login = datetime.utcnow()
            db.session.commit()
            lembrar = session.pop('2fa_lembrar', False)
            session.pop('2fa_user_id', None)
            session.pop('2fa_metodo', None)
            login_user(user, remember=lembrar)
            return redirect(url_for('dashboard'))
        flash('Código incorrecto ou expirado.', 'erro')

    return render_template('auth/verificar_2fa.html', form=form, metodo=metodo, user=user)


# ── Reenviar código ────────────────────────────────────────────────────────

@auth.route('/2fa/reenviar', methods=['POST'])
def reenviar_codigo():
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    metodo = session.get('2fa_metodo', 'telegram')

    if user:
        if metodo == 'telegram':
            enviado = _enviar_codigo_telegram(user)
        else:
            enviado = _enviar_codigo_email(user)

        if enviado:
            flash('Novo código enviado.', 'info')
        else:
            flash('Erro ao reenviar código. Tenta mais tarde.', 'erro')

    return redirect(url_for('auth.verificar_2fa'))


# ── Registo ────────────────────────────────────────────────────────────────

@auth.route('/registo', methods=['GET', 'POST'])
def registo():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistoForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Conta criada com sucesso. Podes iniciar sessão.', 'sucesso')
        return redirect(url_for('auth.login'))

    return render_template('auth/registo.html', form=form)


# ── Perfil ─────────────────────────────────────────────────────────────────

@auth.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    form_password = AlterarPasswordForm(prefix='pwd')
    form_2fa = ConfigurarDoisFAForm(prefix='2fa')

    # Formulário de password
    if form_password.submeter.data and form_password.validate_on_submit():
        if not current_user.check_password(form_password.password_actual.data):
            flash('Palavra-passe actual incorrecta.', 'erro')
        else:
            current_user.set_password(form_password.password_nova.data)
            db.session.commit()
            flash('Palavra-passe alterada com sucesso.', 'sucesso')
            return redirect(url_for('auth.perfil'))

    # Formulário 2FA Telegram
    if form_2fa.submeter_telegram.data and form_2fa.validate_on_submit():
        chat_id = form_2fa.dois_fa_chat_id.data.strip()
        activar = form_2fa.dois_fa_activo.data
        if activar and not chat_id:
            flash('Introduz o Chat ID do Telegram para activar o 2FA via Telegram.', 'erro')
        else:
            current_user.dois_fa_activo = activar
            current_user.dois_fa_chat_id = chat_id or None
            db.session.commit()
            estado = 'activado' if activar else 'desactivado'
            flash(f'2FA via Telegram {estado}.', 'sucesso')
            return redirect(url_for('auth.perfil'))

    # Formulário 2FA Email
    if form_2fa.submeter_email.data and form_2fa.validate_on_submit():
        current_user.dois_fa_email_activo = form_2fa.dois_fa_email_activo.data
        db.session.commit()
        estado = 'activado' if form_2fa.dois_fa_email_activo.data else 'desactivado'
        flash(f'2FA via Email {estado}.', 'sucesso')
        return redirect(url_for('auth.perfil'))

    # Pré-preencher com valores actuais
    if request.method == 'GET':
        form_2fa.dois_fa_activo.data = current_user.dois_fa_activo
        form_2fa.dois_fa_chat_id.data = current_user.dois_fa_chat_id or ''
        form_2fa.dois_fa_email_activo.data = current_user.dois_fa_email_activo

    return render_template('auth/perfil.html', form_password=form_password, form_2fa=form_2fa)


# ── Logout ─────────────────────────────────────────────────────────────────

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão terminada.', 'info')
    return redirect(url_for('auth.login'))
