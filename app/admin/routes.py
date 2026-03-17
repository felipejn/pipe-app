from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from app.admin import admin
from app.admin.decorators import admin_required
from app.auth.models import User


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
