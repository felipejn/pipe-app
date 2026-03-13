import urllib.request
import urllib.error
import json
import time
from datetime import datetime, date, timedelta

API_URL = 'https://euromillions.api.pedromealha.dev/v1/draws'
HEADERS = {'User-Agent': 'PIPE-Euromilhoes/1.0'}

def _fazer_pedido(url, tentativas=3, backoff=5):
    """Faz pedido HTTP com retry exponencial."""
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tentativas - 1:
                time.sleep(backoff * (2 ** i))
            else:
                raise
        except Exception:
            if i < tentativas - 1:
                time.sleep(backoff)
            else:
                raise
    return None

def obter_todos_sorteios():
    """Devolve lista de todos os sorteios históricos."""
    return _fazer_pedido(API_URL)

def obter_ultimo_sorteio():
    """Devolve o sorteio mais recente."""
    sorteios = obter_todos_sorteios()
    if sorteios:
        return max(sorteios, key=lambda s: s['date'])
    return None

def calcular_proximo_sorteio():
    """Calcula a data do próximo sorteio (terça=1 ou sexta=4)."""
    hoje = date.today()
    dias_sorteio = [1, 4]  # Segunda=0, Terça=1, ..., Sexta=4
    for i in range(1, 8):
        proximo = hoje + timedelta(days=i)
        if proximo.weekday() in dias_sorteio:
            return proximo
    return None

def verificar_acertos(numeros_jogados, estrelas_jogadas, sorteio):
    """Compara jogo com sorteio. Devolve (n_acertos, e_acertos, premio)."""
    nums_sorteio = set(str(n) for n in sorteio.get('numbers', []))
    ests_sorteio = set(str(e) for e in sorteio.get('stars', []))
    nums_jogados = set(str(n) for n in numeros_jogados)
    ests_jogados = set(str(e) for e in estrelas_jogadas)

    n_acertos = len(nums_jogados & nums_sorteio)
    e_acertos = len(ests_jogados & ests_sorteio)

    # Procurar prémio correspondente
    premio = 0
    for p in sorteio.get('prizes', []):
        if (p.get('matched_numbers') == n_acertos and
                p.get('matched_stars') == e_acertos):
            premio = p.get('prize', 0)
            break

    return n_acertos, e_acertos, premio
