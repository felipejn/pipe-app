"""Semente de dados para o módulo Combustíveis — concelhos por defeito.

Semeada apenas na criação do primeiro admin (scripts/criar_admin.py).
A função é idempotente: só cria os concelhos se o utilizador ainda não
tiver nenhum, pelo que nunca duplica nem sobrescreve escolhas existentes.
"""
from app import db
from app.combustiveis.models import UtilizadorConcelho

# Nomes exactos usados pela recolha (services.MUNICIPIOS_INTERESSE) e
# pelas rotas /combustiveis/concelhos — mesma grafia/normalização.
CONCELHOS_PREDEFINIDAS = ("Braga", "Vila Verde", "Amares")


def semear_concelhos_predefinidos(user_id):
    """Cria os concelhos predefinidos se o utilizador ainda não tiver nenhum.

    Nunca apaga nem duplica. Não faz commit — deixa a sessão pendente para
    o caller (commit único, tudo ou nada).
    """
    if UtilizadorConcelho.query.filter_by(user_id=user_id).first():
        return
    for concelho in CONCELHOS_PREDEFINIDAS:
        db.session.add(UtilizadorConcelho(user_id=user_id, concelho=concelho))