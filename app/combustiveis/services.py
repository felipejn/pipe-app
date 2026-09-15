"""Serviços do módulo Combustíveis — recolha e consulta de preços.

Fonte de dados: **API Aberta** (api.apiaberta.pt) — API com documentação
Swagger pública em https://api.apiaberta.pt/docs. Substitui os endpoints
diretos da DGEG (precoscombustiveis.dgeg.gov.pt), que não podiam ser
adicionados à whitelist do PythonAnywhere por não terem documentação
pública formal.

Cada página é pedida por combustível (`fuel=<slug>`) e o filtro pelos
concelhos de interesse é feito do lado do cliente, sobre o campo
`municipality`. A atualização é chamada de dois sítios:

- tarefa agendada (só automaticamente às terças-feiras);
- botão manual "Atualizar Dados" (força em qualquer dia).

Regra: NÃO usar subprocess nem chamar scripts externos — tudo é função
Python direta dentro do processo Flask/pipe_tasks.
"""

import os
import time
import requests
from datetime import datetime, date as date_cls
from app import db
from app.combustiveis.models import Posto, PrecoHistorico, EstadoAtualizacaoCombustiveis

BASE_URL = "https://api.apiaberta.pt/v1/fuel/stations"
API_KEY = os.environ.get('APIABERTA_API_KEY')  # opcional; sem chave = 30 req/min

# Combustíveis acompanhados (fuel_slug -> não precisamos do fuel_name aqui,
# vem sempre na própria resposta da API)
FUEL_SLUGS = ["diesel", "diesel_plus", "gasoline_95"]

MUNICIPIOS_INTERESSE = {"Braga", "Vila Verde", "Amares"}

PAGE_LIMIT = 100
# 300 pedidos/minuto com chave (~0,2 s por pedido); 30/minuto sem chave.
# A paginação completa são ~98 pedidos, logo ~21 s com chave.
PAUSA_ENTRE_PEDIDOS = 0.21  # segundos, margem de segurança face ao rate limit
TENTATIVAS_MAX = 3          # tentativas por página antes de desistir do combustível


def _headers():
    headers = {'User-Agent': 'PIPE-combustiveis/1.0 (uso pessoal)'}
    if API_KEY:
        # Confirmado ao vivo: com 'X-API-Key' o x-ratelimit-limit sobe de 30
        # para 300. (O header 'Authorization: Bearer' era ignorado pela API.)
        headers['X-API-Key'] = API_KEY
    return headers


def _obter_estado():
    estado = EstadoAtualizacaoCombustiveis.query.get(1)
    if not estado:
        estado = EstadoAtualizacaoCombustiveis(id=1)
        db.session.add(estado)
        db.session.commit()
    return estado


def _get_com_retry(session, params):
    """GET com retry em 429/5xx — um único 429 não deve descartar ~32 páginas.

    Em 429 respeita o 'Retry-After' devolvido pela API; nas restantes
    tentativas usa backoff exponencial.
    """
    for tentativa in range(1, TENTATIVAS_MAX + 1):
        resp = session.get(BASE_URL, params=params, headers=_headers(), timeout=20)
        if resp.status_code == 429 or resp.status_code >= 500:
            if tentativa == TENTATIVAS_MAX:
                resp.raise_for_status()
                return resp
            espera = PAUSA_ENTRE_PEDIDOS
            try:
                espera = max(espera, float(resp.headers.get('Retry-After', 0)))
            except (TypeError, ValueError):
                pass
            time.sleep(espera * tentativa)
            continue
        resp.raise_for_status()
        return resp
    return resp


def _paginar_fuel(session, fuel_slug):
    """Percorre todas as páginas de um combustível e devolve só os
    registos cujo municipality está em MUNICIPIOS_INTERESSE."""
    encontrados = []
    page = 1
    while True:
        params = {'fuel': fuel_slug, 'page': page, 'limit': PAGE_LIMIT}
        resp = _get_com_retry(session, params)
        corpo = resp.json()

        for registo in corpo.get('data', []):
            if registo.get('municipality') in MUNICIPIOS_INTERESSE:
                encontrados.append(registo)

        meta = corpo.get('meta', {})
        if page >= meta.get('pages', 1):
            break
        page += 1
        time.sleep(PAUSA_ENTRE_PEDIDOS)

        return encontrados


def atualizar_precos_se_necessario(forcar=False, hoje=None):
    """
    Retorna dict: {'executado': bool, 'sucesso': bool, 'postos_atualizados': int, 'erro': str|None}

    Fonte de dados: API Aberta (api.apiaberta.pt/v1/fuel/stations), autenticada
    via header X-API-Key (chave em APIABERTA_API_KEY). Sem chave, tier anónimo
    de 30 pedidos/min; com chave, 300/min. Rate limit respeitado com
    PAUSA_ENTRE_PEDIDOS (~2,1s) e retry em 429 respeitando Retry-After.
    """
    hoje = hoje or date_cls.today()

    if not forcar and hoje.weekday() != 1:  # 1 = terça-feira
        return {'executado': False, 'sucesso': True, 'postos_atualizados': 0, 'erro': None}

    estado = _obter_estado()

    # Evita correr duas vezes na mesma terça-feira, caso a tarefa seja
    # disparada mais do que uma vez no mesmo dia
    if not forcar and estado.ultima_atualizacao and estado.ultima_atualizacao.date() == hoje:
        return {'executado': False, 'sucesso': True, 'postos_atualizados': 0, 'erro': None}

    session = requests.Session()
    erros = []
    postos_vistos = set()

    for fuel_slug in FUEL_SLUGS:
        try:
            registos = _paginar_fuel(session, fuel_slug)
        except requests.RequestException as exc:
            erros.append(f'Falhou fuel={fuel_slug}: {exc}')
            continue

        for r in registos:
            posto_id = r['station_id']
            posto = Posto.query.get(posto_id) or Posto(id=posto_id)
            posto.nome = r.get('name')
            posto.marca = r.get('brand')
            posto.morada = r.get('address')
            posto.localidade = r.get('locality')
            posto.cod_postal = r.get('postal_code')
            posto.concelho = r.get('municipality')
            db.session.add(posto)
            db.session.flush()

            db.session.add(PrecoHistorico(
                posto_id=posto.id,
                tipo_combustivel=r.get('fuel_name'),
                preco=r.get('price_eur'),
                data_atualizacao_dgeg=r.get('updated_at'),
            ))
            postos_vistos.add(posto_id)

    estado.ultima_atualizacao = datetime.utcnow()
    estado.ultima_execucao_sucesso = len(erros) == 0
    estado.mensagem_erro = '; '.join(erros) if erros else None
    db.session.commit()

    return {
        'executado': True,
        'sucesso': len(erros) == 0,
        'postos_atualizados': len(postos_vistos),
        'erro': estado.mensagem_erro,
    }

def obter_tipos_combustivel_disponiveis(concelhos, tipos_utilizador=None):
    query = (
        db.session.query(PrecoHistorico.tipo_combustivel)
        .join(Posto, Posto.id == PrecoHistorico.posto_id)
        .filter(Posto.concelho.in_(concelhos))
    )
    if tipos_utilizador:
        query = query.filter(PrecoHistorico.tipo_combustivel.in_(tipos_utilizador))
    return [t[0] for t in query.distinct().order_by(PrecoHistorico.tipo_combustivel).all()]

def obter_precos_para_concelhos(concelhos, tipos_utilizador=None, tipo_selecionado=None):
    """Últimos preços por posto+combustível, filtrados por concelhos (e, se existir, universo de tipos)."""
    from sqlalchemy import func
    subq = (
        db.session.query(
            PrecoHistorico.posto_id,
            PrecoHistorico.tipo_combustivel,
            func.max(PrecoHistorico.data_recolha).label('max_data')
        )
        .group_by(PrecoHistorico.posto_id, PrecoHistorico.tipo_combustivel)
        .subquery()
    )
    query = (
        db.session.query(Posto, PrecoHistorico)
        .join(PrecoHistorico, PrecoHistorico.posto_id == Posto.id)
        .join(subq, db.and_(
            PrecoHistorico.posto_id == subq.c.posto_id,
            PrecoHistorico.tipo_combustivel == subq.c.tipo_combustivel,
            PrecoHistorico.data_recolha == subq.c.max_data,
        ))
        .filter(Posto.concelho.in_(concelhos))
    )
    if tipos_utilizador:
        query = query.filter(PrecoHistorico.tipo_combustivel.in_(tipos_utilizador))
    if tipo_selecionado and tipo_selecionado != 'Todos':
        query = query.filter(PrecoHistorico.tipo_combustivel == tipo_selecionado)
    return query.order_by(Posto.concelho, PrecoHistorico.tipo_combustivel, PrecoHistorico.preco).all()