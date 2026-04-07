from flask import Blueprint

assistente = Blueprint('assistente', __name__, url_prefix='')

from app.assistente import routes  # noqa: F401, E402
