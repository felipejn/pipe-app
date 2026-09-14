"""Serviços do módulo Combustíveis — recolha e consulta de preços da DGEG.

A atualização de preços só interroga os postos já existentes na tabela
`Posto` (87, restritos a Braga/Vila Verde/Amares) — nunca remapeia
Portugal inteiro. É chamada de dois sítios:

- tarefa agendada (só automaticamente às terças-feiras);
- botão manual "Atualizar Dados" (força em qualquer dia).

Regra: NÃO usar subprocess nem chamar scripts externos — tudo é função
Python direta dentro do processo Flask/pipe_tasks.
"""

import requests
from app import db
from app.combustiveis.models import Posto, PrecoHistorico, EstadoAtualizacaoCombustiveis

DETALHE_URL = "https://precoscombustiveis.dgeg.gov.pt/api/PrecoComb/GetDadosPostoMapa"

def _obter_estado():
    estado = EstadoAtualizacaoCombustiveis.query.get(1)
    if not estado:
        estado = EstadoAtualizacaoCombustiveis(id=1)
        db.session.add(estado)
        db.session.commit()
    return estado

def _extrair_preco(preco_str):
    if not preco_str:
        return None
    try:
        limpo = preco_str.replace('€/litro', '').replace('€', '').replace(',', '.').strip()
        return float(limpo)
    except (ValueError, AttributeError):
        return None

def _fetch_detalhe(session, posto_id):
    try:
        resp = session.get(DETALHE_URL, params={'id': posto_id, 'f': 'json'}, timeout=15)
        resp.raise_for_status()
        dados = resp.json()
        return dados.get('resultado') if dados.get('status') else None
    except requests.RequestException:
        return None

def atualizar_precos_se_necessario(forcar=False, hoje=None):
    """
    Retorna dict: {'executado': bool, 'sucesso': bool, 'postos_atualizados': int, 'erro': str|None}
    """
    from datetime import date as date_cls
    hoje = hoje or date_cls.today()

    if not forcar and hoje.weekday() != 1:  # 1 = terça-feira
        return {'executado': False, 'sucesso': True, 'postos_atualizados': 0, 'erro': None}

    estado = _obter_estado()

    # Evita correr duas vezes na mesma terça-feira, caso a tarefa seja
    # disparada mais do que uma vez no mesmo dia
    if not forcar and estado.ultima_atualizacao and estado.ultima_atualizacao.date() == hoje:
        return {'executado': False, 'sucesso': True, 'postos_atualizados': 0, 'erro': None}

    session = requests.Session()
    session.headers.update({'User-Agent': 'PIPE-combustiveis/1.0 (uso pessoal)'})

    postos = Posto.query.all()
    atualizados = 0
    erros = []

    for posto in postos:
        detalhe = _fetch_detalhe(session, posto.id)
        if detalhe is None:
            erros.append(f'Posto {posto.id} ({posto.nome}) sem resposta')
            continue
        for c in detalhe.get('Combustiveis') or []:
            preco_float = _extrair_preco(c.get('Preco'))
            if preco_float is None:
                continue
            db.session.add(PrecoHistorico(
                posto_id=posto.id,
                tipo_combustivel=c.get('TipoCombustivel'),
                preco=preco_float,
                data_atualizacao_dgeg=detalhe.get('DataAtualizacao'),
            ))
        atualizados += 1

    from datetime import datetime
    estado.ultima_atualizacao = datetime.utcnow()
    estado.ultima_execucao_sucesso = len(erros) == 0
    estado.mensagem_erro = '; '.join(erros) if erros else None
    db.session.commit()

    return {
        'executado': True,
        'sucesso': len(erros) == 0,
        'postos_atualizados': atualizados,
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