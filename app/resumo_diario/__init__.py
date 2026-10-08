"""Módulo Resumo Diário."""

from flask import Blueprint

bp = Blueprint('resumo_diario', __name__, url_prefix='/resumo-diario')

from app.resumo_diario import routes  # noqa: E402,F401
