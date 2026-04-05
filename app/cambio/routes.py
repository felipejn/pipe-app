from flask import render_template, request, jsonify
from flask_login import login_required
from app.cambio import bp
import requests


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


def _obter_cotacoes():
    """Obtem taxa de cambio via ExchangeRate-API (gratuita, sem chave API)."""
    try:
        resp = requests.get('https://api.exchangerate-api.com/v4/latest/EUR', timeout=10)
        resp.raise_for_status()
        dados = resp.json()
        return dados.get('rates', {})
    except Exception:
        return None


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

    taxas = _obter_cotacoes()
    if not taxas:
        return jsonify({'erro': 'Erro ao obter cotações'}), 503

    # API Frankfurter usa EUR como base: taxas[x] = quantas unidades de X por 1 EUR
    taxa_origem = 1.0 if moeda_origem == 'EUR' else taxas.get(moeda_origem, 1)
    taxa_destino = taxas.get(moeda_destino, 1)

    # 1 unidade de origem = (taxa_destino / taxa_origem) unidades de destino
    taxa_directa = round(taxa_destino / taxa_origem, 6)
    resultado = round(valor * taxa_directa, 2)

    return jsonify({
        'origem': moeda_origem,
        'destino': moeda_destino,
        'valor': valor,
        'resultado': resultado,
        'taxa': round(taxa_directa, 4),
    })
