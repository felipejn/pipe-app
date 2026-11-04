"""Cálculo Poupa Mais sem persistir as simulações."""

from app.combustiveis.models import (
    Posto, PrecoHistorico, UtilizadorCombustivel, UtilizadorConcelho,
)
from app.combustiveis import services as combustiveis_services

ESCALOES = (
    (20, 2, 1), (25, 4, 1), (30, 5, 1), (35, 6, 2),
    (40, 7, 2), (45, 8, 3), (50, 9, 3), (55, 10, 4),
    (60, 11, 4), (100.0000001, 12, 6),
)


def calcular_beneficios(litros):
    litros = float(litros)
    bp = saldo = 0
    elegivel = 16 < litros <= 100
    if elegivel:
        for limite, valor_bp, valor_saldo in ESCALOES:
            if litros < limite:
                bp, saldo = valor_bp, valor_saldo
                break
    return {
        'litros': litros, 'bp': bp, 'saldo': saldo, 'total': bp + saldo,
        'elegivel': elegivel, 'fora_tabela': litros > 100,
    }


def obter_opcoes(user_id):
    concelhos = [r.concelho for r in UtilizadorConcelho.query.filter_by(user_id=user_id)]
    tipos = [r.tipo_combustivel for r in UtilizadorCombustivel.query.filter_by(user_id=user_id)]
    if not concelhos or not tipos:
        return [], concelhos, tipos

    duplicados = set(combustiveis_services.obter_ids_duplicados())
    postos = Posto.query.filter(
        Posto.concelho.in_(concelhos), Posto.ativo.is_(True),
    ).order_by(Posto.concelho, Posto.nome).all()
    postos = [p for p in postos if p.id not in duplicados and _posto_elegivel(p)]
    opcoes = []
    for posto in postos:
        for tipo in tipos:
            preco = (PrecoHistorico.query
                     .filter_by(posto_id=posto.id, tipo_combustivel=tipo)
                     .order_by(PrecoHistorico.data_recolha.desc(), PrecoHistorico.id.desc())
                     .first())
            opcoes.append({
                'chave': f'{posto.id}|{tipo}', 'posto': posto, 'tipo': tipo,
                'preco': preco.preco if preco else None,
                'data': (preco.data_atualizacao_dgeg or
                         (preco.data_recolha.strftime('%d/%m/%Y') if preco.data_recolha else None)) if preco else None,
            })
    return opcoes, concelhos, tipos


def _posto_elegivel(posto):
    marca, nome = (posto.marca or '').casefold(), (posto.nome or '').casefold()
    return (marca.strip() == 'bp' or nome.startswith(('bp ', 'bp-')) or 'pingo doce' in marca
            or 'pingo doce' in nome)
