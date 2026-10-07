"""Rotas da Meteorologia — Etapas A (Localizacao) e B (Previsao)."""
from flask import Blueprint, current_app, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import limiter
from app.meteorologia import services
from app.meteorologia.models import LocalizacaoMeteorologia

bp = Blueprint('meteorologia', __name__, url_prefix='/meteorologia')


@bp.route('/localizacao')
@login_required
def localizacao():
    """Pagina de pesquisa e confirmacao da localizacao."""
    local = LocalizacaoMeteorologia.query.filter_by(
        user_id=current_user.id).first()
    return render_template('meteorologia/localizacao.html', local=local)


@bp.route('/api/pesquisar')
@login_required
@limiter.limit('30/minute')
def api_pesquisar():
    """Pesquisa locais (JSON). q vazio -> 400; API em baixo -> 503."""
    termo = (request.args.get('q') or '').strip()
    if not termo:
        return jsonify({'erro': 'Indique um termo de pesquisa.'}), 400
    resultados = services.pesquisar_locais(termo)
    if resultados is None:
        current_app.logger.warning('Geocoding indisponivel')
        return jsonify(
            {'erro': 'Serviço de pesquisa indisponível. Tente mais tarde.'}), 503
    return jsonify({'resultados': resultados})


@bp.route('/api/localizacao', methods=['POST'])
@login_required
@limiter.limit('10/minute')
def api_guardar_localizacao():
    """Guarda a localizacao do utilizador autenticado (JSON)."""
    dados = request.get_json(silent=True) or {}
    ok, erro = services.guardar_localizacao(current_user.id, dados)
    if not ok:
        return jsonify({'erro': erro}), 400
    return jsonify({'ok': True})


@bp.route('/')
@login_required
def index():
    """Etapas A e B. Sem local -> estado vazio; com local e API ok ->
    previsao; com local e API em baixo -> mensagem amigável (200, nunca 500)."""
    local = LocalizacaoMeteorologia.query.filter_by(
        user_id=current_user.id).first()
    previsao, erro = None, None
    if local is not None:
        payload, motivo = services.obter_previsao_utilizador(current_user.id)
        if motivo == 'api_indisponivel':
            erro = 'previsao_indisponivel'
        elif motivo == 'ok':
            previsao = payload
    return render_template(
        'meteorologia/index.html',
        local=local, previsao=previsao, erro=erro, url_localizacao=(
            url_for('meteorologia.localizacao')))
