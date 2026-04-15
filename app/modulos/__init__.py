from flask import Blueprint

modulos_bp = Blueprint('modulos', __name__, url_prefix='/modulos')

from app.modulos import routes