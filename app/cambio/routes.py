from flask import render_template, request, jsonify
from flask_login import login_required
from app.cambio import bp
from app.cambio.service import MOEDAS, obter_taxa



def _obter_taxa(origem, destino, valor):
    """Compatibilidade: delega no serviço partilhado (Wise + fallback)."""
    return obter_taxa(origem, destino, valor)


@bp.route('/')
@login_required
def index():
    return render_template('cambio/index.html', moedas=MOEDAS)


@bp.route('/api/convert', methods=['POST'])
@login_required
def api_convert():
    dados = request.get_json(force=True)
    moeda_origem = dados.get('origem', 'EUR')
    moeda_destino = dados.get('destino', 'BRL')
    valor = float(dados.get('valor', 1))

    resultado = _obter_taxa(moeda_origem, moeda_destino, valor)

    if resultado is None:
        return jsonify({'erro': 'Erro ao obter cotações'}), 503

    return jsonify({
        'origem': moeda_origem,
        'destino': moeda_destino,
        'valor': valor,
        'resultado': resultado['resultado'],
        'taxa': resultado['taxa'],
        'fonte': resultado['fonte'],
        'data': resultado['data'],
        'total_fees': resultado['total_fees'],
        'rate': resultado['rate'],
        'fees': resultado['fees'],
    })
