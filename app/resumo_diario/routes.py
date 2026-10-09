"""Rotas da página e das acções do Resumo Diário."""

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.extensions import limiter
from app.notifications import notification_service
from app.resumo_diario import bp
from app.resumo_diario.services import (
    OPCOES_POR_OMISSAO,
    gerar_resumo_diario,
    ler_configuracao_resumo_diario,
    obter_data_local,
    obter_ou_criar_configuracao,
)


@bp.route('/definicoes', methods=['GET', 'POST'])
@login_required
def definicoes():
    if request.method == 'POST':
        configuracao = obter_ou_criar_configuracao(current_user.id)
        for nome in OPCOES_POR_OMISSAO:
            setattr(configuracao, nome, nome in request.form)
        db.session.commit()
        flash('Definições guardadas com sucesso.', 'sucesso')
        return redirect(url_for('resumo_diario.definicoes'))

    # A consulta da página é só de leitura: a linha nasce ao guardar.
    return render_template(
        'resumo_diario/definicoes.html',
        opcoes=ler_configuracao_resumo_diario(current_user.id),
    )


@bp.route('/api/previsualizar', methods=['POST'])
@login_required
@limiter.limit('10/minute')
def previsualizar():
    resumo = gerar_resumo_diario(current_user.id, obter_data_local(), modo='web')
    return jsonify({'ok': True, 'data': resumo['data'], 'texto': resumo['texto'],
                    'origem': resumo.get('origem'), 'motivo': resumo.get('motivo')})


@bp.route('/api/enviar', methods=['POST'])
@login_required
@limiter.limit('5/hour')
def enviar():
    preferencias = current_user.notificacao_prefs
    chat_id = (preferencias.telegram_chat_id or '').strip() if preferencias else ''
    if not chat_id:
        return jsonify({
            'ok': False,
            'mensagem': 'Configura primeiro o chat_id do Telegram nas definições de notificações.',
        }), 400

    resumo = gerar_resumo_diario(current_user.id, obter_data_local(), modo='web')
    # O envio manual é uma acção explícita do utilizador: exige chat_id, mas
    # ignora telegram_activo. A futura entrega automática deverá respeitar essa
    # preferência e continuar a usar o comportamento normal do serviço.
    resultado = notification_service.send(
        user=current_user,
        type='resumo_diario',
        subject='Resumo Diário',
        body=resumo['texto'] or 'Não há novidades para hoje.',
        force_channel='telegram',
        telegram_parse_mode='HTML',
    )
    if resultado.get('telegram') is None:
        return jsonify({
            'ok': False,
            'mensagem': 'O Telegram não está configurado no servidor. Tenta mais tarde.',
        }), 503
    if not resultado.get('telegram'):
        return jsonify({
            'ok': False,
            'mensagem': 'Não foi possível enviar o resumo pelo Telegram. Confirma o chat_id e tenta novamente.',
        }), 502
    return jsonify({'ok': True, 'mensagem': 'Resumo enviado por Telegram.'})
