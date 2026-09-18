"""Serviço partilhado de taxas de câmbio (Wise + fallback).

Extraído de `routes.py` para poder ser reutilizado pelo Assistente IA
(ferramenta `get_cambio`) sem duplicar lógica nem acoplamento ao Blueprint.
"""

import os

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


def obter_taxa(origem, destino, valor):
    """Obtém taxa de câmbio via Wise API v3 (com taxas reais incluídas).
    Fallback para ExchangeRate-API se Wise falhar.
    """
    wise_key = os.environ.get('WISE_API_KEY', '')
    try:
        headers = {'Content-Type': 'application/json'}
        if wise_key:
            headers['Authorization'] = f'Bearer {wise_key}'

        resp = requests.post(
            'https://api.wise.com/v3/quotes',
            headers=headers,
            json={'sourceCurrency': origem, 'targetCurrency': destino, 'sourceAmount': valor},
            timeout=8,
        )
        resp.raise_for_status()
        dados = resp.json()
        opcoes = dados.get('paymentOptions', [])
        if not opcoes:
            raise ValueError('Sem paymentOptions na resposta Wise')
        opcoes_activas = [o for o in opcoes if not o.get('disabled', False)]
        if not opcoes_activas:
            raise ValueError('Sem paymentOptions activas na resposta Wise')
        # Use DEBIT as default (matches Wise website default display)
        debit = next((o for o in opcoes_activas if o.get('payIn') == 'DEBIT'), None)
        melhor = debit if debit else opcoes_activas[0]
        target_amount = melhor.get('targetAmount', 0)
        fee_data = melhor.get('fee', {})
        price_data = melhor.get('price', {})
        fees_items = price_data.get('items', [])
        taxa_efectiva = target_amount / valor if valor else 0
        return {
            'resultado': round(target_amount, 2),
            'taxa': round(taxa_efectiva, 4),
            'fonte': 'Wise',
            'data': dados.get('rateTimestamp'),
            'total_fees': fee_data.get('total'),
            'rate': dados.get('rate'),
            'fees': [
                {
                    'label': f.get('label', ''),
                    'amount': f['value']['amount'],
                    'currency': f['value']['currency'],
                }
                for f in fees_items
                if f.get('value', {}).get('amount', 0) > 0
            ],
        }
    except Exception:
        pass

    try:
        rates_resp = requests.get(f'https://api.exchangerate-api.com/v4/latest/{origem}', timeout=8)
        rates_resp.raise_for_status()
        taxas = rates_resp.json().get('rates', {})
        taxa = taxas.get(destino, 1)
        resultado = round(valor * taxa, 2)
        return {
            'resultado': resultado,
            'taxa': round(taxa, 4),
            'fonte': 'ExchangeRate-API',
            'data': None,
            'total_fees': None,
            'rate': None,
            'fees': [],
        }
    except Exception:
        return None


# Alias de compatibilidade com o nome antigo usado nas rotas.
obter_taxa_cambio = obter_taxa
