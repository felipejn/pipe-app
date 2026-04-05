import requests
from flask import render_template, request, jsonify
from flask_login import login_required
from app.cambio import bp


# Wise API - funciona sem token autenticado
WISE_BASE_URL = 'https://api.wise.com/v3/quotes'

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


def _obter_todas_taxas(moeda_base='EUR'):
    """Obtem taxas em lote via Wise API (sem token)."""
    try:
        taxas = {}
        moeda_codes = list(MOEDAS.keys())
        for code in moeda_codes:
            if code == moeda_base:
                continue
            resp = requests.post(
                WISE_BASE_URL,
                headers={'Content-Type': 'application/json'},
                json={'sourceCurrency': moeda_base, 'targetCurrency': code, 'sourceAmount': 10000},
                timeout=10,
            )
            if resp.status_code == 200:
                dados = resp.json()
                taxas[code] = dados.get('rate')
        return taxas or None
    except Exception:
        return None


def _obter_taxa_directa(origem, destino, valor=1):
    """Obtem taxa directa de uma conversao especifica via Wise API."""
    try:
        # sourceAmount em centimos (ex: 1.50 -> 150)
        source_cents = round(valor * 100, 0)
        resp = requests.post(
            WISE_BASE_URL,
            headers={'Content-Type': 'application/json'},
            json={
                'sourceCurrency': origem,
                'targetCurrency': destino,
                'sourceAmount': source_cents,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            dados = resp.json()
            return {
                'rate': dados.get('rate'),
                'target_amount': dados.get('targetAmount'),
                'source_currency': dados.get('sourceCurrency'),
                'target_currency': dados.get('targetCurrency'),
                'rate_timestamp': dados.get('rateTimestamp'),
            }
        return None
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

    resultado_wise = _obter_taxa_directa(moeda_origem, moeda_destino, valor)

    if not resultado_wise:
        return jsonify({'erro': 'Erro ao obter cotações da Wise'}), 503

    taxa = resultado_wise['rate']
    resultado = resultado_wise['target_amount']

    return jsonify({
        'origem': moeda_origem,
        'destino': moeda_destino,
        'valor': valor,
        'resultado': round(resultado, 2),
        'taxa': round(taxa, 4),
        'fonte': 'Wise',
        'data': resultado_wise.get('rate_timestamp', ''),
    })
