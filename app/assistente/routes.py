"""Rotas do módulo Assistente IA.

- GET  /assistente          — página temporária de placeholder
- POST /assistente/api/chat — API AJAX {mensagem: "..."} → {resposta: "..."}
"""

from flask import jsonify, request, render_template
from flask_login import login_required, current_user

from app.assistente import assistente
from app.assistente.contexto import processar_mensagem_assistente
from app.extensions import limiter


@assistente.route('/assistente', strict_slashes=False)
@login_required
def index():
    """Página do Assistente PIPE — interface de chat."""
    return render_template('assistente/index.html')


@assistente.route('/assistente/api/chat', methods=['POST'])
@login_required
@limiter.limit('30 per minute')
def api_chat():
    """Endpoint AJAX para o chat com o Assistente IA.

    Recebe JSON com {mensagem: "..."} e devolve {resposta: "..."}.
    """
    dados = request.get_json(silent=True)
    if not dados or 'mensagem' not in dados:
        return jsonify({'erro': 'Campo "mensagem" obrigatório.'}), 400

    mensagem = dados['mensagem'].strip()
    if not mensagem:
        return jsonify({'erro': 'A mensagem não pode estar vazia.'}), 400

    resposta = processar_mensagem_assistente(mensagem, user_id=current_user.id)
    return jsonify({'resposta': resposta})


@assistente.route('/assistente/api/limpar', methods=['POST'])
@login_required
@limiter.limit('10 per minute')
def api_limpar():
    """Limpa o histórico de conversa da sessão."""
    from flask import session
    session.pop('chat_historico', None)
    return jsonify({'ok': True})
