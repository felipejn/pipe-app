from flask import Blueprint

notas = Blueprint('notas', __name__)

from app.notas import routes  # noqa: F401, E402
