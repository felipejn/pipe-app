import secrets
from datetime import datetime, timedelta

from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app import db
from app.admin import admin
from app.admin.decorators import admin_required
from app.auth.models import User, Convite
from app.notifications.channels.email import EmailChannel


# ── Dashboard ──────────────────────────────────────────────────────────────

@admin.route('/')
@login_required
@admin_required
def dashboard():
    """Painel principal de administração."""
    total_utilizadores = User.query.count()
    utilizadores_activos = User.query.filter_by(activo=True).count()
    total_admins = User.query.filter_by(is_admin=True).count()

    ultimos_utilizadores = (
        User.query.order_by(User.data_criacao.desc()).limit(5).all()
    )

    return render_template(
        'admin/dashboard.html',
        total_utilizadores=total_utilizadores,
        utilizadores_activos=utilizadores_activos,
        total_admins=total_admins,
        ultimos_utilizadores=ultimos_utilizadores,
    )

# ── Utilizadores ───────────────────────────────────────────────────────────

@admin.route('/utilizadores')
@login_required
@admin_required
def utilizadores():
    """Lista todos os utilizadores."""
    todos = User.query.order_by(User.data_criacao.desc()).all()
    return render_template('admin/utilizadores.html', utilizadores=todos)


@admin.route('/utilizadores/<int:user_id>/toggle-activo', methods=['POST'])
@login_required
@admin_required
def toggle_activo(user_id):
    """Activa ou desactiva um utilizador."""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('Não podes desactivar a tua própria conta.', 'erro')
        return redirect(url_for('admin.utilizadores'))

    user.activo = not user.activo
    db.session.commit()

    estado = 'activado' if user.activo else 'desactivado'
    flash(f'Utilizador {user.username} {estado}.', 'sucesso')
    return redirect(url_for('admin.utilizadores'))


@admin.route('/utilizadores/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Promove ou rebaixa um utilizador a admin."""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('Não podes alterar o teu próprio estatuto de admin.', 'erro')
        return redirect(url_for('admin.utilizadores'))

    user.is_admin = not user.is_admin
    db.session.commit()

    estado = 'promovido a admin' if user.is_admin else 'removido de admin'
    flash(f'Utilizador {user.username} {estado}.', 'sucesso')
    return redirect(url_for('admin.utilizadores'))


@admin.route('/utilizadores/<int:user_id>/apagar', methods=['POST'])
@login_required
@admin_required
def apagar_utilizador(user_id):
    """Apaga um utilizador e todos os dados associados."""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('Não podes apagar a tua própria conta.', 'erro')
        return redirect(url_for('admin.utilizadores'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f'Utilizador {username} apagado.', 'sucesso')
    return redirect(url_for('admin.utilizadores'))


# ── Convites ───────────────────────────────────────────────────────────────

@admin.route('/convites')
@login_required
@admin_required
def convites():
    """Lista todos os convites, com estado (activo/usado/expirado)."""
    todos = Convite.query.order_by(Convite.criado_em.desc()).all()
    return render_template('admin/convites.html', convites=todos)


@admin.route('/convites/gerar', methods=['POST'])
@login_required
@admin_required
def gerar_convite():
    """Gera um novo convite para um email."""
    dados = request.get_json()
    email = dados.get('email', '').strip().lower()
    enviar_email = dados.get('enviar_email', False)

    if not email or '@' not in email:
        return {'erro': 'Email inválido.'}, 400

    token = secrets.token_urlsafe(32)
    convite = Convite(
        token=token,
        email=email,
        criado_por=current_user.id,
        expira_em=datetime.utcnow() + timedelta(days=7),
    )
    db.session.add(convite)
    db.session.commit()

    link = url_for('auth.registo_com_convite', token=token, _external=True)

    if enviar_email:
        try:
            api_key = current_app.config.get('MAILJET_API_KEY')
            api_secret = current_app.config.get('MAILJET_API_SECRET')
            remetente = current_app.config.get('MAILJET_FROM_EMAIL')
            current_app.logger.info(f'[MAILJET] API key configurada: {bool(api_key)}, remetente: {remetente}')
            canal = EmailChannel(api_key=api_key, api_secret=api_secret, remetente=remetente)

            # Criar objecto utilizador simulado com o email do convite
            class _Destinatario:
                email = convite.email
                username = 'convidado'

            current_app.logger.info(f'Enviando convite por email para {convite.email}')
            enviado = canal.enviar(
                _Destinatario(),
                assunto='Convite para a plataforma PIPE',
                corpo=(
                    f'Olá,\n\n'
                    f'Foste convidado a juntar-te à plataforma PIPE.\n\n'
                    f'Clica no link abaixo para criar a tua conta (válido durante 7 dias):\n\n'
                    f'{link}\n\n'
                    f'Se não esperavas este convite, podes ignorar esta mensagem.'
                ),
            )
            current_app.logger.info(f'Resultado do envio: {enviado}')
            res = getattr(canal, 'ultimo_resultado', None) or {}
            current_app.logger.info(
                f"[MAILJET] message_id={res.get('message_id')} erro={res.get('erro')}")

            if enviado:
                # Guardar a confirmação: o ID do Mailjet permite depois verificar
                # a entrega real (entregue / falhou com o motivo) no painel.
                convite.mailjet_message_id = (
                    str(res['message_id']) if res.get('message_id') else None)
                convite.email_estado = 'aceite'
                db.session.commit()
                return {'sucesso': True, 'link': link, 'email_enviado': True,
                        'message_id': convite.mailjet_message_id}

            convite.email_estado = 'falhou'
            db.session.commit()
            if res.get('erro'):
                return {'erro': f"Falha no envio: {res['erro']}", 'link': link}, 500
            return {'erro': 'Falha no envio (Mailjet retornou false).', 'link': link}, 500

        except Exception as e:
            current_app.logger.exception('Exceção ao enviar convite por email')
            # Em desenvolvimento, devolver mensagem detalhada para debug
            if current_app.debug:
                return {'erro': f'Exceção: {str(e)}', 'link': link}, 500
            return {'erro': 'Erro ao enviar email. Tenta novamente.', 'link': link}, 500

    return {'sucesso': True, 'link': link, 'email_enviado': False}


@admin.route('/convites/<int:convite_id>/estado-email')
@login_required
@admin_required
def estado_email(convite_id):
    """Consulta ao Mailjet o estado real de entrega do email do convite.

    O «Convite enviado» do painel só prova que a API aceitou o pedido; esta rota
    mostra se a mensagem foi efectivamente entregue, rejeitada (com o motivo do
    bounce — ex.: `550 5.7.40` do Gmail por falta de autenticação do domínio
    remetente) ou se ainda não há confirmação. O resultado é guardado no convite.
    """
    convite = Convite.query.get_or_404(convite_id)

    if not convite.mailjet_message_id:
        return {'erro': 'Convite sem ID no Mailjet — não há mensagem para verificar '
                        '(gerado sem envio de email, ou anterior ao registo de IDs; '
                        'para convites antigos usa scripts/verificar_mailjet.py).'}, 400

    api_key = current_app.config.get('MAILJET_API_KEY')
    api_secret = current_app.config.get('MAILJET_API_SECRET')
    if not (api_key and api_secret):
        return {'erro': 'Mailjet não está configurado neste servidor.'}, 400

    canal = EmailChannel(api_key=api_key, api_secret=api_secret,
                         remetente=current_app.config.get('MAILJET_FROM_EMAIL'))
    resultado = canal.consultar_estado(convite.mailjet_message_id)

    if resultado.get('erro'):
        return {'erro': f"Falha ao consultar o Mailjet: {resultado['erro']}"}, 502

    if resultado.get('estado'):
        convite.email_estado = resultado['estado']
    convite.email_verificado_em = datetime.utcnow()
    db.session.commit()

    rotulo, classe = convite.estado_email() or (convite.email_estado or '?',
                                                'badge-inactivo')
    return {
        'sucesso': True,
        'estado': convite.email_estado,
        'rotulo': rotulo,
        'classe': classe,
        'eventos': resultado.get('eventos', []),
        'motivo': resultado.get('motivo'),
        'verificado_em': convite.email_verificado_em.strftime('%d/%m/%Y %H:%M'),
    }


@admin.route('/convites/<int:convite_id>/revogar', methods=['POST'])
@login_required
@admin_required
def revogar_convite(convite_id):
    """Revoga um convite não utilizado."""
    convite = Convite.query.get_or_404(convite_id)

    if convite.usado:
        flash('Não é possível revogar um convite já utilizado.', 'erro')
        return redirect(url_for('admin.convites'))

    convite.usado = True
    convite.usado_em = datetime.utcnow()
    db.session.commit()

    flash(f'Convite para {convite.email} revogado.', 'sucesso')
    return redirect(url_for('admin.convites'))
