from flask import Blueprint

calendario_bp = Blueprint('calendario', __name__)

from app.calendario import routes
