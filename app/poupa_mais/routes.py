from decimal import Decimal, InvalidOperation

from flask import render_template, request, session
from flask_login import current_user, login_required

from app.poupa_mais import bp
from app.poupa_mais.services import calcular_beneficios, obter_opcoes


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    opcoes, concelhos, tipos = obter_opcoes(current_user.id)
    chave_guardada = session.get('poupa_mais_posto')
    selecionada = next((o for o in opcoes if o['chave'] == chave_guardada), opcoes[0] if opcoes else None)
    resultado = erro = None
    if request.method == 'POST':
        chave, modo = request.form.get('posto_combustivel', ''), request.form.get('modo')
        opcao = next((o for o in opcoes if o['chave'] == chave), None)
        if opcao:
            session['poupa_mais_posto'] = chave
            selecionada = opcao
        try:
            quantidade = Decimal(request.form.get('quantidade', '').replace(',', '.'))
            if not quantidade.is_finite() or quantidade <= 0 or not opcao or modo not in ('euros', 'litros'):
                raise ValueError
            preco = (Decimal(str(opcao['preco'])) if opcao['preco'] is not None else
                     Decimal(request.form.get('preco_manual', '').replace(',', '.')))
            if not preco.is_finite() or preco <= 0:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError):
            erro = 'Indica um posto, uma quantidade e um preço válidos.'
        else:
            litros = float(quantidade / preco if modo == 'euros' else quantidade)
            valor_abastecimento = float(quantidade if modo == 'euros' else quantidade * preco)
            resultado = calcular_beneficios(litros)
            resultado.update({
                'posto': opcao['posto'].nome, 'combustivel': opcao['tipo'],
                'preco': float(preco), 'data': opcao['data'],
                'valor_abastecimento': valor_abastecimento,
                'valor_apos_desconto': max(valor_abastecimento - resultado['bp'], 0),
                'preco_efectivo': max(valor_abastecimento - resultado['bp'], 0) / litros,
            })
    return render_template('poupa_mais/index.html', opcoes=opcoes,
                           concelhos=concelhos, tipos=tipos,
                           resultado=resultado, erro=erro, selecionada=selecionada)
