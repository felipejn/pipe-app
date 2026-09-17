"""Rotas do módulo Assistente IA.

- GET  /assistente            — página do assistente (interface de chat)
- POST /assistente/api/chat   — API AJAX {mensagem: "..."} → {resposta: "..."}
- POST /assistente/api/modo   — alterna entre modo leitura e escrita
- POST /assistente/api/limpar — limpa o histórico de conversa
"""

from flask import jsonify, request, render_template, session
from flask_login import login_required, current_user

from app.assistente import assistente
from app.assistente.contexto import processar_mensagem_assistente
from app.extensions import limiter


@assistente.route('/assistente', strict_slashes=False)
@login_required
def index():
    """Página do Assistente PIPE — interface de chat."""
    modo = session.get('assistente_modo', 'leitura')
    return render_template('assistente/index.html', modo=modo)


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

    resposta_texto, modelo = processar_mensagem_assistente(mensagem, user_id=current_user.id)
    return jsonify({'resposta': resposta_texto, 'modelo': modelo})


@assistente.route('/assistente/api/limpar', methods=['POST'])
@login_required
@limiter.limit('10 per minute')
def api_limpar():
    """Limpa o histórico de conversa da sessão."""
    session.pop('chat_historico', None)
    return jsonify({'ok': True})


@assistente.route('/assistente/api/modo', methods=['POST'])
@login_required
@limiter.limit('10 per minute')
def api_modo():
    """Alterna entre modo leitura e modo escrita do assistente.

    Recebe JSON com {modo: "leitura"|"escrita"} e grava na sessão.
    """
    dados = request.get_json(silent=True) or {}
    modo = dados.get('modo')
    if modo not in ('leitura', 'escrita'):
        return jsonify({'erro': 'Modo inválido. Usa "leitura" ou "escrita".'}), 400

    session['assistente_modo'] = modo
    return jsonify({'ok': True, 'modo': modo})
