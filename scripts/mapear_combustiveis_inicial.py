"""
mapear_combustiveis_inicial.py — Primeira recolha real de postos de combustível.

Script AVULSO, para correr manualmente UMA VEZ:
    python scripts/mapear_combustiveis_inicial.py

- Recolhe o catálogo completo de postos da DGEG, filtra para a zona
  Braga / Vila Verde / Amares e grava os dados nos modelos do PIPE
  (Posto e PrecoHistorico).
- NÃO faz parte da tarefa agendada (pipe_tasks.py) nem é chamado a
  partir de nenhuma rota web — demora alguns minutos e o free tier do
  PythonAnywhere tem timeout no pedido HTTP.
- NOTA (produção/PA): confirmar que o domínio
  precoscombustiveis.dgeg.gov.pt está na whitelist do PythonAnywhere
  antes de correr (em localhost o requests normal funciona sem whitelist).
"""

import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

import requests
import concurrent.futures
from app import create_app, db
from app.combustiveis.models import Posto, PrecoHistorico

LISTAR_URL = "https://precoscombustiveis.dgeg.gov.pt/api/PrecoComb/ListarDadosPostos"
DETALHE_URL = "https://precoscombustiveis.dgeg.gov.pt/api/PrecoComb/GetDadosPostoMapa"
CONCURRENCY = 10

KEYWORDS = ["braga", "vila verde", "amares"]
CP_PREFIXOS = {
    "4700", "4701", "4702", "4703", "4704", "4705", "4706", "4707",
    "4708", "4709", "4710", "4711", "4712", "4713", "4714", "4715",
    "4716", "4717", "4719",  # Braga
    "4720",                  # Amares
    "4730", "4731", "4734",  # Vila Verde
}

def deduzir_concelho(cod_postal, localidade, morada):
    cp = (cod_postal or "")[:4]
    loc = ((localidade or "") + " " + (morada or "")).lower()
    if cp.startswith("4720") or "amares" in loc:
        return "Amares"
    if cp in {"4730", "4731", "4734"} or "vila verde" in loc:
        return "Vila Verde"
    return "Braga"

def pertence_a_zona(cod_postal, localidade, morada):
    cp = (cod_postal or "")[:4]
    loc = ((localidade or "") + " " + (morada or "")).lower()
    if cp in CP_PREFIXOS:
        return True
    return any(kw in loc for kw in KEYWORDS)

def extrair_preco(preco_str):
    if not preco_str:
        return None
    try:
        limpo = preco_str.replace('€/litro', '').replace('€', '').replace(',', '.').strip()
        return float(limpo)
    except (ValueError, AttributeError):
        return None

def obter_detalhe(session, posto_id):
    try:
        resp = session.get(DETALHE_URL, params={'id': posto_id, 'f': 'json'}, timeout=15)
        resp.raise_for_status()
        dados = resp.json()
        return dados.get('resultado') if dados.get('status') else None
    except requests.RequestException as exc:
        print(f'  [aviso] falhou posto {posto_id}: {exc}')
        return None

def main():
    app = create_app()
    with app.app_context():
        session = requests.Session()
        session.headers.update({'User-Agent': 'PIPE-combustiveis/1.0 (uso pessoal)'})

        print('A obter lista de todos os postos de Portugal Continental...')
        resp = session.get(LISTAR_URL, timeout=15)
        resp.raise_for_status()
        ids = [p['Id'] for p in resp.json()['resultado']]
        print(f'  -> {len(ids)} postos no total.')

        print(f'A consultar detalhe (concorrência={CONCURRENCY})...')
        encontrados = 0
        processados = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futuros = {executor.submit(obter_detalhe, session, pid): pid for pid in ids}
            for futuro in concurrent.futures.as_completed(futuros):
                pid = futuros[futuro]
                detalhe = futuro.result()
                processados += 1

                if detalhe is None:
                    continue

                morada = detalhe.get('Morada') or {}
                if not pertence_a_zona(morada.get('CodPostal'), morada.get('Localidade'), morada.get('Morada')):
                    continue

                concelho = deduzir_concelho(morada.get('CodPostal'), morada.get('Localidade'), morada.get('Morada'))

                posto = Posto.query.get(pid) or Posto(id=pid)
                posto.nome = detalhe.get('Nome')
                posto.marca = detalhe.get('Marca')
                posto.tipo_posto = detalhe.get('TipoPosto')
                posto.morada = morada.get('Morada')
                posto.localidade = morada.get('Localidade')
                posto.cod_postal = morada.get('CodPostal')
                posto.concelho = concelho
                db.session.add(posto)
                db.session.flush()  # garante posto.id disponível para o FK abaixo

                for c in detalhe.get('Combustiveis') or []:
                    preco_float = extrair_preco(c.get('Preco'))
                    if preco_float is None:
                        continue
                    db.session.add(PrecoHistorico(
                        posto_id=posto.id,
                        tipo_combustivel=c.get('TipoCombustivel'),
                        preco=preco_float,
                        data_atualizacao_dgeg=detalhe.get('DataAtualizacao'),
                    ))

                encontrados += 1
                print(f'  [{processados}/{len(ids)}] + {detalhe.get("Nome")} ({concelho})')

                if processados % 200 == 0:
                    db.session.commit()

        db.session.commit()
        print(f'\nMapeamento concluído: {encontrados} postos guardados (Braga/Vila Verde/Amares).')

if __name__ == '__main__':
    main()