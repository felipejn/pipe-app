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
    """Página de resultados — verifica acertos dos jogos registados."""
    periodo = request.args.get('periodo', 'ultimo')

    # Determinar intervalo de datas
    hoje = date.today()
    if periodo == '30':
        data_inicio = hoje - timedelta(days=30)
    elif periodo == '90':
        data_inicio = hoje - timedelta(days=90)
    elif periodo == 'todos':
        data_inicio = date(2004, 1, 1)  # Euromilhões começou em 2004
    else:
        # Último sorteio: calcular a data do sorteio mais recente passado
        data_inicio = hoje - timedelta(days=7)
        periodo = 'ultimo'

    # Obter jogos do utilizador no período
    jogos = Jogo.query.filter_by(user_id=current_user.id)\
                      .filter(Jogo.data_sorteio >= data_inicio)\
                      .filter(Jogo.data_sorteio <= hoje)\
                      .order_by(Jogo.data_sorteio.desc()).all()

    # Obter sorteios históricos da API
    sorteios_api = []
    erro_api = None
    try:
        todos = euro_api.obter_todos_sorteios()
        if todos:
            # Filtrar sorteios no período
            sorteios_api = [
                s for s in todos
                if data_inicio <= datetime.strptime(s['date'], '%Y-%m-%d').date() <= hoje
            ]
    except Exception as ex:
        erro_api = 'Não foi possível contactar a API. Tenta novamente mais tarde.'

    # Cruzar jogos com sorteios
    resultados_jogos = []
    total_ganho = 0

    for jogo in jogos:
        # Encontrar o sorteio correspondente à data do jogo
        sorteio_match = next(
            (s for s in sorteios_api
             if datetime.strptime(s['date'], '%Y-%m-%d').date() == jogo.data_sorteio),
            None
        )

        if sorteio_match:
            n_ac, e_ac, premio = euro_api.verificar_acertos(
                jogo.get_numeros(), jogo.get_estrelas(), sorteio_match
            )
            total_ganho += premio
            resultados_jogos.append({
                'jogo': jogo,
                'sorteio': sorteio_match,
                'n_acertos': n_ac,
                'e_acertos': e_ac,
                'premio': premio,
                'tem_resultado': True,
            })
        else:
            # Sorteio ainda não aconteceu ou não está na API
            resultados_jogos.append({
                'jogo': jogo,
                'sorteio': None,
                'n_acertos': 0,
                'e_acertos': 0,
                'premio': 0,
                'tem_resultado': False,
            })

    return render_template('euromilhoes/resultados.html',
                           resultados=resultados_jogos,
                           total_ganho=total_ganho,
                           periodo=periodo,
                           erro_api=erro_api)


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

            # Números 1-50 com percentagem e proporção para barra visual
            max_num = max(cont_nums.values()) if cont_nums else 1
            for n in range(1, 51):
                count = cont_nums.get(n, 0)
                freq_numeros.append({
                    'valor': n,
                    'count': count,
                    'pct': round(count / total_sorteios * 100, 1) if total_sorteios else 0,
                    'proporcao': round(count / max_num * 100, 1) if max_num else 0,
                })

            # Estrelas 1-12
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

    # Top 5 mais e menos frequentes
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
