from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.modulos.models import UserModulo, get_modulos_ativos
from app.modulos.config import MODULOS_DISPONIVEIS
from app.modulos import modulos_bp

@modulos_bp.route('/loja')
@login_required
def loja():
    modulos_ativos = get_modulos_ativos(current_user.id)
    return render_template('modulos/loja.html', modulos=MODULOS_DISPONIVEIS, modulos_ativos=modulos_ativos)

@modulos_bp.route('/api/toggle', methods=['POST'])
@login_required
def toggle():
    data = request.get_json()
    modulo_slug = data.get('modulo_slug')
    user_id = data.get('user_id')
    ativo = data.get('ativo')

    user_modulo = UserModulo.query.filter_by(user_id=user_id, modulo_slug=modulo_slug).first()
    if user_modulo:
        user_modulo.ativo = ativo
        db.session.commit()
    else:
        user_modulo = UserModulo(user_id=user_id, modulo_slug=modulo_slug, ativo=ativo)
        db.session.add(user_modulo)
        db.session.commit()

    return jsonify({'ok': True, 'slug': modulo_slug, 'ativo': ativo})