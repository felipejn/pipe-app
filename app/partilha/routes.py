from flask import abort, current_app, jsonify, render_template, request
from flask_login import login_required, current_user

from app import db
from app.auth.models import User
from app.extensions import limiter
from app.notifications import notification_service
from app.partilha import partilha_bp
from app.partilha.models import PartilhaRecurso
from app.partilha.utils import (
    pode_aceder_recurso,
    obter_recurso_ou_404,
    _obter_modelo,
)


def _resolver_utilizador_por_email(email):
    """Devolve o User correspondente ao email, ou None se nao existir."""
    if not email:
        return None
    return User.query.filter_by(email=email.strip().lower()).first()


def _tipo_valido(tipo_recurso):
    return tipo_recurso in ('tarefa', 'nota', 'evento')


# ── Rotas estáticas primeiro (evitam conflito com /<tipo_recurso>/<int:>) ─────

@partilha_bp.route('/minhas', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def partilhadas_comigo():
    """Lista recursos partilhados com o utilizador autenticado (estado aceite)."""
    partilhas = PartilhaRecurso.query.filter_by(
        utilizador_id=current_user.id, estado='aceite',
    ).all()

    resultado = []
    for p in partilhas:
        modelo = _obter_modelo(p.tipo_recurso)
        recurso = modelo.query.filter_by(id=p.recurso_id).first()
        if recurso is None:
            continue
        resultado.append({
            'partilha_id': p.id,
            'tipo_recurso': p.tipo_recurso,
            'recurso_id': p.recurso_id,
            'nivel': p.nivel,
            'dono_id': p.dono_id,
            'dono_email': p.dono.email,
            'titulo': getattr(recurso, 'texto', None)
                      or getattr(recurso, 'titulo', f'{p.tipo_recurso} #{p.recurso_id}'),
        })

    return jsonify(resultado)


@partilha_bp.route('/criadas', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def partilhas_criadas():
    """Lista partilhas que o utilizador autenticado criou (é o dono)."""
    partilhas = PartilhaRecurso.query.filter_by(dono_id=current_user.id).all()
    resultado = []
    for p in partilhas:
        modelo = _obter_modelo(p.tipo_recurso)
        recurso = modelo.query.filter_by(id=p.recurso_id).first() if modelo else None
        resultado.append({
            'id': p.id,
            'tipo_recurso': p.tipo_recurso,
            'recurso_id': p.recurso_id,
            'titulo': (
                getattr(recurso, 'texto', None) or getattr(recurso, 'titulo', None)
                if recurso else None
            ) or f'{p.tipo_recurso} #{p.recurso_id}',
            'utilizador_id': p.utilizador_id,
            'utilizador_email': p.utilizador.email,
            'utilizador_nome': p.utilizador.nome_apresentacao,
            'nivel': p.nivel,
            'estado': p.estado,
            'criado_em': p.criado_em.isoformat() if p.criado_em else None,
        })
    return jsonify(resultado)


@partilha_bp.route('/pendentes', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def partilhas_pendentes():
    """Lista convites pendentes recebidos pelo utilizador autenticado."""
    partilhas = PartilhaRecurso.query.filter_by(
        utilizador_id=current_user.id, estado='pendente',
    ).all()

    resultado = []
    for p in partilhas:
        modelo = _obter_modelo(p.tipo_recurso)
        recurso = modelo.query.filter_by(id=p.recurso_id).first()
        if recurso is None:
            continue
        resultado.append({
            'partilha_id': p.id,
            'tipo_recurso': p.tipo_recurso,
            'recurso_id': p.recurso_id,
            'nivel': p.nivel,
            'dono_email': p.dono.email,
            'titulo': getattr(recurso, 'texto', None)
                      or getattr(recurso, 'titulo', f'{p.tipo_recurso} #{p.recurso_id}'),
        })

    return jsonify(resultado)


@partilha_bp.route('/convites', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def gerir_convites():
    """Apresenta a página de gestão de convites recebidos."""
    return render_template('partilha/convites.html')


# ── Rotas com segmento estático (antes de /<tipo_recurso>/<int:>) ─────────────

@partilha_bp.route('/<int:partilha_id>/aceitar', methods=['POST'])
@login_required
@limiter.limit("10/minute")
def aceitar_partilha(partilha_id):
    """Aceita uma partilha recebida pelo utilizador autenticado."""
    partilha = PartilhaRecurso.query.filter_by(
        id=partilha_id, utilizador_id=current_user.id, estado='pendente',
    ).first_or_404()

    partilha.estado = 'aceite'
    db.session.commit()

    return jsonify({'ok': True, 'estado': partilha.estado})


@partilha_bp.route('/<int:partilha_id>/rejeitar', methods=['POST'])
@login_required
@limiter.limit("10/minute")
def rejeitar_partilha(partilha_id):
    """Rejeita uma partilha recebida pelo utilizador autenticado."""
    partilha = PartilhaRecurso.query.filter_by(
        id=partilha_id, utilizador_id=current_user.id, estado='pendente',
    ).first_or_404()

    partilha.estado = 'rejeitado'
    db.session.commit()

    return jsonify({'ok': True, 'estado': partilha.estado})


@partilha_bp.route('/<int:partilha_id>', methods=['DELETE'])
@login_required
@limiter.limit("10/minute")
def remover_partilha(partilha_id):
    """Remove/cancela uma partilha. Apenas o dono ou o utilizador alvo pode remover."""
    partilha = PartilhaRecurso.query.filter_by(id=partilha_id).first_or_404()

    if partilha.dono_id != current_user.id and partilha.utilizador_id != current_user.id:
        abort(404)

    db.session.delete(partilha)
    db.session.commit()

    return jsonify({'ok': True})


# ── Rotas genéricas por tipo de recurso (por último) ──────────────────────────

@partilha_bp.route('/<tipo_recurso>/<int:recurso_id>', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def listar_partilhas_recurso(tipo_recurso, recurso_id):
    """Lista as partilhas de um recurso. Apenas o dono pode listar."""
    if not _tipo_valido(tipo_recurso):
        abort(404)

    modelo = _obter_modelo(tipo_recurso)
    recurso = modelo.query.filter_by(id=recurso_id, user_id=current_user.id).first()
    if recurso is None:
        abort(404)

    partilhas = PartilhaRecurso.query.filter_by(
        tipo_recurso=tipo_recurso, recurso_id=recurso_id,
    ).all()

    return jsonify([
        {
            'id': p.id,
            'utilizador_id': p.utilizador_id,
            'utilizador_email': p.utilizador.email,
            'utilizador_nome': p.utilizador.nome_apresentacao,
            'nivel': p.nivel,
            'estado': p.estado,
            'criado_em': p.criado_em.isoformat() if p.criado_em else None,
            'actualizado_em': p.actualizado_em.isoformat() if p.actualizado_em else None,
        }
        for p in partilhas
    ])


@partilha_bp.route('/<tipo_recurso>/<int:recurso_id>', methods=['POST'])
@login_required
@limiter.limit("10/minute")
def criar_partilha(tipo_recurso, recurso_id):
    """Cria uma partilha de um recurso para outro utilizador (identificado por email).

    Body JSON: { "email": "utilizador@exemplo.com", "nivel": "leitura" | "edicao" }
    """
    if not _tipo_valido(tipo_recurso):
        abort(404)

    dados = request.get_json(silent=True) or {}
    email = (dados.get('email') or '').strip().lower()
    nivel = (dados.get('nivel') or 'leitura').strip()

    if nivel not in ('leitura', 'edicao'):
        return jsonify({'erro': 'Nivel invalido. Use "leitura" ou "edicao".'}), 400

    if not email:
        return jsonify({'erro': 'Email nao fornecido.'}), 400

    modelo = _obter_modelo(tipo_recurso)
    recurso = modelo.query.filter_by(id=recurso_id, user_id=current_user.id).first()
    if recurso is None:
        abort(404)

    utilizador_alvo = _resolver_utilizador_por_email(email)
    if utilizador_alvo is None:
        return jsonify({'erro': 'Nao existe utilizador registado com esse email.'}), 404

    if utilizador_alvo.id == current_user.id:
        return jsonify({'erro': 'Nao se pode partilhar consigo mesmo.'}), 400

    # Não permitir partilha ativa duplicada (pendente ou aceite) para o mesmo utilizador.
    existente = PartilhaRecurso.query.filter_by(
        tipo_recurso=tipo_recurso, recurso_id=recurso_id, utilizador_id=utilizador_alvo.id,
    ).filter(PartilhaRecurso.estado != 'rejeitado').first()
    if existente is not None:
        return jsonify({'erro': 'Ja existe uma partilha ativa para este utilizador.'}), 400

    partilha = PartilhaRecurso(
        tipo_recurso=tipo_recurso,
        recurso_id=recurso_id,
        dono_id=current_user.id,
        utilizador_id=utilizador_alvo.id,
        nivel=nivel,
        estado='pendente',
    )
    db.session.add(partilha)
    db.session.commit()

    # Notificar o utilizador alvo.
    try:
        artigo_tipo = {
            'tarefa': 'a tarefa',
            'nota': 'a nota',
            'evento': 'o compromisso',
        }[tipo_recurso]
        titulo_recurso = getattr(recurso, 'texto', None) or getattr(
            recurso, 'titulo', f'{tipo_recurso} #{recurso.id}'
        )
        resultado_notificacao = notification_service.send(
            user=utilizador_alvo,
            type='partilha_recurso',
            subject='Recebeu um convite para um recurso partilhado',
            body=(
                f'O utilizador {current_user.nome_apresentacao} partilhou consigo '
                f'{artigo_tipo} "{titulo_recurso}" com permissao de "{nivel}". '
                f'Aceite ou rejeite em /partilha/convites.'
            ),
            data={
                'partilha_id': partilha.id,
                'tipo_recurso': tipo_recurso,
                'recurso_id': recurso_id,
                'dono_id': current_user.id,
                'nivel': nivel,
            },
            force_channel='email',
        )
        if resultado_notificacao.get('email') is not True:
            current_app.logger.warning(
                'Notificacao de partilha nao entregue (partilha_id=%s, motivo=%s)',
                partilha.id,
                notification_service.ultimo_erro('email') or 'canal de email indisponivel',
            )
    except Exception:
        current_app.logger.warning(
            'Falha ao enviar notificacao de partilha (partilha_id=%s)', partilha.id
        )

    return jsonify({
        'id': partilha.id,
        'utilizador_id': utilizador_alvo.id,
        'utilizador_email': utilizador_alvo.email,
        'nivel': partilha.nivel,
        'estado': partilha.estado,
    }), 201
