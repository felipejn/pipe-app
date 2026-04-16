from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.calendario import calendario_bp
from app.calendario.models import Evento
from app import db
from app.extensions import limiter
from datetime import datetime

@calendario_bp.route('/')
@login_required
@limiter.limit("60/minute")
def index():
    return render_template('calendario/index.html')

@calendario_bp.route('/api/eventos')
@login_required
@limiter.limit("60/minute")
def api_eventos():
    inicio = request.args.get('inicio')
    fim    = request.args.get('fim')
    eventos = Evento.query.filter(
        Evento.user_id     == current_user.id,
        Evento.data_inicio <  datetime.fromisoformat(fim),
        Evento.data_fim    >  datetime.fromisoformat(inicio)
    ).all()
    return jsonify([{
        'id':          e.id,
        'titulo':      e.titulo,
        'descricao':   e.descricao,
        'localizacao': e.localizacao,
        'data_inicio': e.data_inicio.isoformat(),
        'data_fim':    e.data_fim.isoformat(),
        'dia_inteiro': e.dia_inteiro,
        'cor':         e.cor,
        'notificar':   e.notificar
    } for e in eventos])

@calendario_bp.route('/api/eventos', methods=['POST'])
@login_required
@limiter.limit("30/minute")
def api_criar_evento():
    dados = request.get_json()
    inicio = datetime.fromisoformat(dados['data_inicio'])
    fim    = datetime.fromisoformat(dados['data_fim'])
    if fim < inicio:
        return jsonify({'erro': 'A data de fim não pode ser anterior à data de início.'}), 400
    evento = Evento(
        user_id     = current_user.id,
        titulo      = dados['titulo'],
        descricao   = dados.get('descricao'),
        localizacao = dados.get('localizacao'),
        data_inicio = inicio,
        data_fim    = fim,
        dia_inteiro = dados.get('dia_inteiro', False),
        cor         = dados.get('cor', 'tomate'),
        notificar   = dados.get('notificar', True)
    )
    db.session.add(evento)
    db.session.commit()
    return jsonify({'id': evento.id}), 201

@calendario_bp.route('/api/eventos/<int:id>', methods=['PUT'])
@login_required
@limiter.limit("30/minute")
def api_editar_evento(id):
    evento = Evento.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    dados  = request.get_json()
    inicio = datetime.fromisoformat(dados['data_inicio'])
    fim    = datetime.fromisoformat(dados['data_fim'])
    if fim < inicio:
        return jsonify({'erro': 'A data de fim não pode ser anterior à data de início.'}), 400
    evento.titulo        = dados.get('titulo', evento.titulo)
    evento.descricao     = dados.get('descricao', evento.descricao)
    evento.localizacao   = dados.get('localizacao', evento.localizacao)
    evento.data_inicio   = inicio
    evento.data_fim      = fim
    evento.dia_inteiro   = dados.get('dia_inteiro', evento.dia_inteiro)
    evento.cor           = dados.get('cor', evento.cor)
    evento.notificar     = dados.get('notificar', evento.notificar)
    evento.notificado_em = None
    db.session.commit()
    return jsonify({'ok': True})

@calendario_bp.route('/api/eventos/<int:id>', methods=['DELETE'])
@login_required
@limiter.limit("30/minute")
def api_apagar_evento(id):
    evento = Evento.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(evento)
    db.session.commit()
    return jsonify({'ok': True})
