import requests
from flask import render_template, request, jsonify
from flask_login import login_required
from app.cambio import bp


MOEDAS = {
    'EUR': 'Euro (€)',
    'BRL': 'Real brasileiro (R$)',
    'USD': 'Dólar americano ($)',
    'GBP': 'Libra esterlina (£)',
    'JPY': 'Iene japonês (¥)',
    'CHF': 'Franco suíço (Fr)',
    'CAD': 'Dólar canadense (C$)',
    'AUD': 'Dólar australiano (A$)',
}


def _obter_taxa(origem, destino, valor):
    """Obtem taxa de cambio. Tenta Wise first, fallback exchangerate-api."""
    # 1) Wise API (requer whitelist no PA)
    try:
        source_cents = round(valor * 100)
        resp = requests.post(
            'https://api.wise.com/v3/quotes',
            headers={'Content-Type': 'application/json'},
            json={'sourceCurrency': origem, 'targetCurrency': destino, 'sourceAmount': source_cents},
            timeout=8,
        )
        if resp.status_code == 200:
            dados = resp.json()
            return dados.get('targetAmount'), dados.get('rate'), 'Wise', dados.get('rateTimestamp')
    except Exception:
        pass

    # 2) Fallback: exchangerate-api
    try:
        rates_resp = requests.get(f'https://api.exchangerate-api.com/v4/latest/{origem}', timeout=8)
        rates_resp.raise_for_status()
        taxas = rates_resp.json().get('rates', {})
        taxa = taxas.get(destino, 1)
        resultado = round(valor * taxa, 2)
        return resultado, round(taxa, 4), 'ExchangeRate-API', None
    except Exception:
        return None, None, None, None


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

    resultado, taxa, fonte, data = _obter_taxa(moeda_origem, moeda_destino, valor)

    if resultado is None:
        return jsonify({'erro': 'Erro ao obter cotações'}), 503

    return jsonify({
        'origem': moeda_origem,
        'destino': moeda_destino,
        'valor': valor,
        'resultado': round(resultado, 2),
        'taxa': round(taxa, 4) if taxa else None,
        'fonte': fonte,
        'data': data,
    })
