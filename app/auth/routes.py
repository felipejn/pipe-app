import random
import os
import io
import base64
import secrets
from datetime import datetime, timedelta

import qrcode
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.auth import auth
from app.auth.forms import (
    LoginForm, RegistoForm, AlterarPasswordForm,
    VerificarCodigoForm, ConfigurarDoisFAForm, ConfirmarTOTPForm,
    PedirResetForm, ResetPasswordForm
)
from app.auth.models import User, Convite
from app.extensions import limiter
from app.notifications.channels.telegram import TelegramChannel
from app.notifications.channels.email import EmailChannel
from flask import current_app
from flask_limiter.errors import RateLimitExceeded


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
@limiter.limit("10 per minute", methods=["POST"])
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
                login_user(user, remember=True)
                session.permanent = True
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

        app.logger.warning('Login falhado para utilizador: %s (IP: %s)',
                            form.username.data, request.remote_addr)
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

    if metodo == 'totp':
        # TOTP não envia código — redireciona directamente para verificação
        return redirect(url_for('auth.verificar_2fa'))

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
@limiter.limit("10 per minute", methods=["POST"])
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
        if metodo == 'totp':
            valido = user.verificar_totp(form.codigo.data)
        else:
            valido = user.codigo_valido(form.codigo.data)
            if valido:
                user.limpar_codigo()

            if valido:
                user.ultimo_login = datetime.utcnow()
                db.session.commit()
                session.pop('2fa_user_id', None)
                session.pop('2fa_metodo', None)
                login_user(user, remember=True)
                session.permanent = True
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

@auth.route('/registo')
def registo():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    flash('O registo requer um convite.', 'info')
    return redirect(url_for('auth.login'))


# ── Registo com convite ────────────────────────────────────────────────────

@auth.route('/registo/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per hour", methods=["POST"])
def registo_com_convite(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    convite = Convite.query.filter_by(token=token).first()

    if not convite:
        flash('Convite inválido.', 'erro')
        return redirect(url_for('auth.login'))

    if convite.usado:
        flash('Este convite já foi utilizado.', 'erro')
        return redirect(url_for('auth.login'))

    if not convite.esta_valido():
        flash('Este convite expirou.', 'erro')
        return redirect(url_for('auth.login'))

    # Formulário com email pré-preenchido
    form = RegistoForm()
    if request.method == 'GET':
        form.email.data = convite.email

    if form.validate_on_submit():
        if form.email.data.lower() != convite.email.strip().lower():
            flash('O email deve corresponder ao do convite.', 'erro')
            return render_template('auth/registo_token.html', form=form, convite=convite)

        user = User(username=form.username.data, email=form.email.data.lower().strip())
        user.set_password(form.password.data)
        db.session.add(user)

        convite.usado = True
        convite.usado_em = datetime.utcnow()
        db.session.commit()

        flash('Conta criada com sucesso. Podes iniciar sessão.', 'sucesso')
        return redirect(url_for('auth.login'))

    return render_template('auth/registo_token.html', form=form, convite=convite)


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


# ── TOTP — configurar ─────────────────────────────────────────────────────

def _gerar_qrcode_base64(uri):
    """Gera um QR code a partir do URI e devolve como string base64 PNG."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


@auth.route('/2fa/totp/configurar', methods=['GET', 'POST'])
@login_required
def configurar_totp():
    """Gera um novo secret TOTP e mostra o QR code para o utilizador digitalizar."""
    form = ConfirmarTOTPForm()

    if request.method == 'GET':
        # Gera sempre um secret novo (sobrescreve qualquer anterior não confirmado)
        current_user.gerar_totp_secret()
        current_user.totp_activo = False  # Só activa após confirmação
        db.session.commit()

    uri = current_user.totp_uri()
    qr_b64 = _gerar_qrcode_base64(uri)

    if form.validate_on_submit():
        # Valida o código antes de activar
        import pyotp
        totp = pyotp.TOTP(current_user.totp_secret)
        if totp.verify(form.codigo.data.strip(), valid_window=1):
            current_user.totp_activo = True
            db.session.commit()
            flash('Autenticador configurado com sucesso.', 'sucesso')
            return redirect(url_for('auth.perfil'))
        flash('Código incorrecto. Verifica o teu autenticador e tenta novamente.', 'erro')

    return render_template(
        'auth/configurar_totp.html',
        form=form,
        qr_b64=qr_b64,
        totp_secret=current_user.totp_secret
    )


@auth.route('/2fa/totp/desactivar', methods=['POST'])
@login_required
def desactivar_totp():
    """Desactiva e apaga o TOTP do utilizador."""
    current_user.totp_activo = False
    current_user.totp_secret = None
    db.session.commit()
    flash('Autenticador desactivado.', 'sucesso')
    return redirect(url_for('auth.perfil'))


# ── Recuperação de password ────────────────────────────────────────────────

@auth.route('/recuperar-password', methods=['GET', 'POST'])
@limiter.limit("5 per hour", methods=["POST"])
def recuperar_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = PedirResetForm()
    mensagem = None

    if form.validate_on_submit():
        utilizador = User.query.filter_by(email=form.email.data.strip().lower()).first()

        if utilizador:
            token = secrets.token_urlsafe(32)
            utilizador.reset_token = token
            utilizador.reset_token_expira = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            link = url_for('auth.reset_password', token=token, _external=True)
            api_key = current_app.config.get('SENDGRID_API_KEY')
            remetente = current_app.config.get('SENDGRID_FROM_EMAIL')
            canal = EmailChannel(api_key=api_key, remetente=remetente)
            canal.enviar(
                utilizador,
                assunto='PIPE — Recuperação de palavra-passe',
                corpo=(
                    f'Olá {utilizador.username},\n\n'
                    f'Recebemos um pedido de recuperação de palavra-passe para a tua conta PIPE.\n\n'
                    f'Clica no link abaixo para definir uma nova palavra-passe (válido durante 1 hora):\n\n'
                    f'{link}\n\n'
                    f'Se não fizeste este pedido, ignora este email — a tua conta está segura.'
                ),
            )

        # Resposta sempre igual — evita enumeração de emails
        mensagem = 'Se o email existir na plataforma, receberás um link em breve.'

    return render_template('auth/recuperar_password.html', form=form, mensagem=mensagem)


# ── Handler de erro rate limiting ──────────────────────────────────────────

@auth.app_errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    form = LoginForm()
    return render_template('auth/login.html',
        form=form,
        erro_limite="Demasiadas tentativas. Aguarda um momento antes de tentar novamente."
    ), 429


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    utilizador = User.query.filter_by(reset_token=token).first()

    if not utilizador or utilizador.reset_token_expira < datetime.utcnow():
        flash('O link de recuperação é inválido ou expirou.', 'erro')
        return redirect(url_for('auth.recuperar_password'))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        utilizador.set_password(form.password_nova.data)
        utilizador.reset_token = None
        utilizador.reset_token_expira = None
        db.session.commit()
        flash('Palavra-passe alterada com sucesso. Podes iniciar sessão.', 'sucesso')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)


# ── Logout ─────────────────────────────────────────────────────────────────

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão terminada.', 'info')
    return redirect(url_for('auth.login'))
