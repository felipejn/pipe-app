from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime
import random
from app import db
from app.euromilhoes import euromilhoes
from app.euromilhoes.models import Jogo
from app.euromilhoes import api as euro_api

@euromilhoes.route('/')
@login_required
def index():
    jogos = Jogo.query.filter_by(user_id=current_user.id)\
                      .order_by(Jogo.data_sorteio.desc()).all()
    proximo = euro_api.calcular_proximo_sorteio()
    return render_template('euromilhoes/index.html',
                           jogos=jogos,
                           proximo_sorteio=proximo)

@euromilhoes.route('/registar', methods=['POST'])
@login_required
def registar_jogo():
    numeros = request.form.getlist('numeros')
    estrelas = request.form.getlist('estrelas')
    data_sorteio_str = request.form.get('data_sorteio')

    # Validação
    erros = []
    if len(numeros) != 5:
        erros.append('Selecciona exactamente 5 números.')
    if len(estrelas) != 2:
        erros.append('Selecciona exactamente 2 estrelas.')

    try:
        data_sorteio = datetime.strptime(data_sorteio_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        erros.append('Data de sorteio inválida.')
        data_sorteio = None

    if erros:
        for e in erros:
            flash(e, 'erro')
        return redirect(url_for('euromilhoes.index'))

    jogo = Jogo(user_id=current_user.id, data_sorteio=data_sorteio)
    jogo.set_numeros([int(n) for n in numeros])
    jogo.set_estrelas([int(e) for e in estrelas])
    db.session.add(jogo)
    db.session.commit()
    flash('Jogo registado com sucesso!', 'sucesso')
    return redirect(url_for('euromilhoes.index'))

@euromilhoes.route('/apagar/<int:jogo_id>', methods=['POST'])
@login_required
def apagar_jogo(jogo_id):
    jogo = Jogo.query.filter_by(id=jogo_id, user_id=current_user.id).first_or_404()
    db.session.delete(jogo)
    db.session.commit()
    flash('Jogo apagado.', 'info')
    return redirect(url_for('euromilhoes.index'))

@euromilhoes.route('/gerar')
@login_required
def gerar_combinacao():
    """API endpoint — devolve combinação aleatória em JSON."""
    numeros = sorted(random.sample(range(1, 51), 5))
    estrelas = sorted(random.sample(range(1, 13), 2))
    return jsonify({'numeros': numeros, 'estrelas': estrelas})

@euromilhoes.route('/ultimo-sorteio')
@login_required
def ultimo_sorteio():
    try:
        sorteio = euro_api.obter_ultimo_sorteio()
    except Exception:
        sorteio = None
    return render_template('euromilhoes/index.html', ultimo_sorteio=sorteio)
