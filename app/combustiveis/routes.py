from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.combustiveis.models import Posto, UtilizadorConcelho
from app.combustiveis import services
from app.extensions import limiter

bp = Blueprint('combustiveis', __name__, url_prefix='/combustiveis')

@bp.route('/')
@login_required
def dashboard():
    from app.combustiveis.models import UtilizadorCombustivel, EstadoAtualizacaoCombustiveis

    concelhos_utilizador = [
        uc.concelho for uc in UtilizadorConcelho.query.filter_by(user_id=current_user.id).all()
    ]
    if not concelhos_utilizador:
        return redirect(url_for('combustiveis.definicoes'))

    tipos_utilizador = [
        uc.tipo_combustivel for uc in UtilizadorCombustivel.query.filter_by(user_id=current_user.id).all()
    ]

    tipo_selecionado = request.args.get('combustivel', 'Todos')
    tipos_disponiveis = ['Todos'] + services.obter_tipos_combustivel_disponiveis(concelhos_utilizador, tipos_utilizador)

    # Se o utilizador tinha escolhido um combustível específico que já não
    # está no universo (ex.: removeu-o nas Definições), volta a "Todos"
    if tipo_selecionado not in tipos_disponiveis:
        tipo_selecionado = 'Todos'

    resultados = services.obter_precos_para_concelhos(concelhos_utilizador, tipos_utilizador, tipo_selecionado)

    # Estado da recolha — mostrado no cabeçalho para o utilizador perceber se os
    # preços são frescos ou se a última tentativa falhou.
    estado = EstadoAtualizacaoCombustiveis.query.get(1)
    # Conta só postos activos e NÃO obsoletos — os arquivados já não aparecem
    # na tabela (filtro em obter_precos_para_concelhos), e os obsoletos
    # (dados DGEG congelados, como o DJB) tampoco devem figurar no total,
    # senão o cabeçalho diria "N postos" e a tabela mostraria menos.
    total_postos = (Posto.query
                    .filter(Posto.ativo.is_(True),
                            ~Posto.id.in_(services.obter_ids_postos_obsoletos()))
                    .count())

    return render_template('combustiveis/dashboard.html',
                            resultados=resultados,
                            tipos_disponiveis=tipos_disponiveis,
                            tipo_selecionado=tipo_selecionado,
                            estado=estado,
                            total_postos=total_postos)

@bp.route('/definicoes', methods=['GET', 'POST'])
@login_required
def definicoes():
    from app.combustiveis.models import UtilizadorCombustivel
    from app.combustiveis.models import PrecoHistorico

    concelhos_disponiveis = [
        c[0] for c in db.session.query(Posto.concelho).distinct().order_by(Posto.concelho).all()
    ]
    tipos_disponiveis = [
        t[0] for t in db.session.query(PrecoHistorico.tipo_combustivel)
        .distinct().order_by(PrecoHistorico.tipo_combustivel).all()
    ]

    if request.method == 'POST':
        # CSRF: usar o input hidden csrf_token, NUNCA csrf_field() — ver regras do projeto
        selecionados = request.form.getlist('concelhos')
        UtilizadorConcelho.query.filter_by(user_id=current_user.id).delete()
        for c in selecionados:
            if c in concelhos_disponiveis:
                db.session.add(UtilizadorConcelho(user_id=current_user.id, concelho=c))

        # Combustíveis de interesse — gravar (apagar anteriores e inserir as novas)
        combustiveis_selecionados = request.form.getlist('combustiveis')
        UtilizadorCombustivel.query.filter_by(user_id=current_user.id).delete()
        for t in combustiveis_selecionados:
            if t in tipos_disponiveis:
                db.session.add(UtilizadorCombustivel(user_id=current_user.id, tipo_combustivel=t))

        db.session.commit()
        flash('Preferências guardadas.', 'success')
        return redirect(url_for('combustiveis.dashboard'))

    atuais = {uc.concelho for uc in UtilizadorConcelho.query.filter_by(user_id=current_user.id).all()}
    combustiveis_atuais = {
        uc.tipo_combustivel for uc in UtilizadorCombustivel.query.filter_by(user_id=current_user.id).all()
    }
    return render_template('combustiveis/definicoes.html',
                            concelhos_disponiveis=concelhos_disponiveis,
                            concelhos_atuais=atuais,
                            tipos_disponiveis=tipos_disponiveis,
                            combustiveis_atuais=combustiveis_atuais)

@bp.route('/atualizar', methods=['POST'])
@limiter.limit("6/hour", methods=["POST"])
@login_required
def atualizar():
    resultado = services.atualizar_precos_se_necessario(forcar=True)

    # Reporta os postos arquivados apenas quando existem, para não poluir a
    # mensagem no caso normal (a maioria das recolhas não arquiva nada).
    sufixo_arquivados = ''
    if resultado['postos_arquivados']:
        # Concordância singular/plural, como no cabeçalho do dashboard.
        n = resultado['postos_arquivados']
        s = 's' if n != 1 else ''
        sufixo_arquivados = f" {n} posto{s} arquivado{s} (deixaram de aparecer na API)."

    if not resultado['sucesso']:
        flash(f"Actualização com erros ({resultado['postos_verificados']} postos "
              f"verificados antes da falha): {resultado['erro']}", 'warning')
    elif resultado['precos_novos']:
        flash(f"Preços actualizados — {resultado['postos_verificados']} postos "
              f"verificados, {resultado['precos_novos']} registos novos.{sufixo_arquivados}", 'success')
    else:
        flash(f"Preços verificados — {resultado['postos_verificados']} postos, "
              f"sem alterações desde a última recolha.{sufixo_arquivados}", 'success')

    return redirect(url_for('combustiveis.dashboard'))