import secrets
from datetime import datetime, timedelta

from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app import db
from app.admin import admin
from app.admin.decorators import admin_required
from app.auth.models import User, Convite
from app.partilha.models import PartilhaRecurso
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
    PartilhaRecurso.query.filter(
        db.or_(
            PartilhaRecurso.dono_id == user.id,
            PartilhaRecurso.utilizador_id == user.id,
        )
    ).delete(synchronize_session=False)
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
            canal = EmailChannel(
                client_id=current_app.config.get('ZOHO_CLIENT_ID'),
                client_secret=current_app.config.get('ZOHO_CLIENT_SECRET'),
                refresh_token=current_app.config.get('ZOHO_REFRESH_TOKEN'),
                account_id=current_app.config.get('ZOHO_ACCOUNT_ID'),
                remetente=current_app.config.get('ZOHO_FROM_EMAIL'),
                dc=current_app.config.get('ZOHO_DC', 'eu'),
            )

            # Criar objecto utilizador simulado com o email do convite
            class _Destinatario:
                email = convite.email
                username = 'convidado'

            current_app.logger.info(f'Enviando convite por email para {convite.email}')
            enviado = canal.enviar_template(
                _Destinatario(), 'convite', {'link': link})
            res = getattr(canal, 'ultimo_resultado', None) or {}

            if enviado:
                convite.email_message_id = (
                    str(res['message_id']) if res.get('message_id') else None)
                convite.email_estado = 'enviado'
                db.session.commit()
                return {'sucesso': True, 'link': link, 'email_enviado': True,
                        'message_id': convite.email_message_id}

            convite.email_estado = 'falhou'
            db.session.commit()
            return {'erro': 'Falha no envio pelo Zoho Mail.', 'link': link}, 500

        except Exception as e:
            current_app.logger.error('Excepção ao enviar convite por email: %s', type(e).__name__)
            convite.email_estado = 'falhou'
            db.session.commit()
            return {'erro': 'Erro ao enviar email. Tenta novamente.', 'link': link}, 500

    return {'sucesso': True, 'link': link, 'email_enviado': False}


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
