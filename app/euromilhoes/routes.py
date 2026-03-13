from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from collections import Counter
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
    """Endpoint JSON — devolve combinação aleatória."""
    numeros = sorted(random.sample(range(1, 51), 5))
    estrelas = sorted(random.sample(range(1, 13), 2))
    return jsonify({'numeros': numeros, 'estrelas': estrelas})


@euromilhoes.route('/resultados')
@login_required
def resultados():
    """Página de resultados — carrega imediatamente com jogos locais.
    Os acertos são preenchidos via fetch ao endpoint /resultados/dados."""
    periodo = request.args.get('periodo', 'ultimo')
    hoje = date.today()

    if periodo == '30':
        data_inicio = hoje - timedelta(days=30)
    elif periodo == '90':
        data_inicio = hoje - timedelta(days=90)
    elif periodo == 'todos':
        data_inicio = date(2004, 1, 1)
    else:
        data_inicio = hoje - timedelta(days=7)
        periodo = 'ultimo'

    jogos = Jogo.query.filter_by(user_id=current_user.id)\
                      .filter(Jogo.data_sorteio >= data_inicio)\
                      .filter(Jogo.data_sorteio <= hoje)\
                      .order_by(Jogo.data_sorteio.desc()).all()

    return render_template('euromilhoes/resultados.html',
                           jogos=jogos,
                           periodo=periodo)


@euromilhoes.route('/resultados/dados')
@login_required
def resultados_dados():
    """Endpoint JSON — faz chamada à API e devolve acertos calculados."""
    periodo = request.args.get('periodo', 'ultimo')
    hoje = date.today()

    if periodo == '30':
        data_inicio = hoje - timedelta(days=30)
    elif periodo == '90':
        data_inicio = hoje - timedelta(days=90)
    elif periodo == 'todos':
        data_inicio = date(2004, 1, 1)
    else:
        data_inicio = hoje - timedelta(days=7)

    jogos = Jogo.query.filter_by(user_id=current_user.id)\
                      .filter(Jogo.data_sorteio >= data_inicio)\
                      .filter(Jogo.data_sorteio <= hoje)\
                      .order_by(Jogo.data_sorteio.desc()).all()

    try:
        todos = euro_api.obter_todos_sorteios()
    except Exception:
        return jsonify({'erro': 'Não foi possível contactar a API. Tenta novamente mais tarde.'})

    sorteios_por_data = {}
    if todos:
        for s in todos:
            sorteios_por_data[s['date']] = s

    resultados_json = []
    total_ganho = 0

    for jogo in jogos:
        data_str = jogo.data_sorteio.strftime('%Y-%m-%d')
        sorteio = sorteios_por_data.get(data_str)

        if sorteio:
            n_ac, e_ac, premio = euro_api.verificar_acertos(
                jogo.get_numeros(), jogo.get_estrelas(), sorteio
            )
            total_ganho += premio
            resultados_json.append({
                'jogo_id': jogo.id,
                'n_acertos': n_ac,
                'e_acertos': e_ac,
                'premio': premio,
                'numeros_sorteio': sorteio.get('numbers', []),
                'estrelas_sorteio': sorteio.get('stars', []),
                'tem_resultado': True,
            })
        else:
            resultados_json.append({
                'jogo_id': jogo.id,
                'n_acertos': 0,
                'e_acertos': 0,
                'premio': 0,
                'numeros_sorteio': [],
                'estrelas_sorteio': [],
                'tem_resultado': False,
            })

    return jsonify({'resultados': resultados_json, 'total_ganho': total_ganho})


@euromilhoes.route('/frequencias')
@login_required
def frequencias():
    """Página de análise de frequências históricas."""
    erro_api = None
    freq_numeros = []
    freq_estrelas = []
    total_sorteios = 0

    try:
        todos = euro_api.obter_todos_sorteios()
        if todos:
            total_sorteios = len(todos)
            cont_nums = Counter()
            cont_ests = Counter()

            for s in todos:
                for n in s.get('numbers', []):
                    cont_nums[int(n)] += 1
                for e in s.get('stars', []):
                    cont_ests[int(e)] += 1

            max_num = max(cont_nums.values()) if cont_nums else 1
            for n in range(1, 51):
                count = cont_nums.get(n, 0)
                freq_numeros.append({
                    'valor': n,
                    'count': count,
                    'pct': round(count / total_sorteios * 100, 1) if total_sorteios else 0,
                    'proporcao': round(count / max_num * 100, 1) if max_num else 0,
                })

            max_est = max(cont_ests.values()) if cont_ests else 1
            for e in range(1, 13):
                count = cont_ests.get(e, 0)
                freq_estrelas.append({
                    'valor': e,
                    'count': count,
                    'pct': round(count / total_sorteios * 100, 1) if total_sorteios else 0,
                    'proporcao': round(count / max_est * 100, 1) if max_est else 0,
                })

    except Exception:
        erro_api = 'Não foi possível contactar a API. Tenta novamente mais tarde.'

    top5_nums = sorted(freq_numeros, key=lambda x: x['count'], reverse=True)[:5]
    bot5_nums = sorted(freq_numeros, key=lambda x: x['count'])[:5]
    top3_ests = sorted(freq_estrelas, key=lambda x: x['count'], reverse=True)[:3]
    bot3_ests = sorted(freq_estrelas, key=lambda x: x['count'])[:3]

    return render_template('euromilhoes/frequencias.html',
                           freq_numeros=freq_numeros,
                           freq_estrelas=freq_estrelas,
                           top5_nums=top5_nums,
                           bot5_nums=bot5_nums,
                           top3_ests=top3_ests,
                           bot3_ests=bot3_ests,
                           total_sorteios=total_sorteios,
                           erro_api=erro_api)
