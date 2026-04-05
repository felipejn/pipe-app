from flask import Blueprint

bp = Blueprint('cambio', __name__)

from app.cambio import routes  # noqa: E402, F401
