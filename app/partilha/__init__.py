from flask import Blueprint

partilha_bp = Blueprint('partilha', __name__, url_prefix='/partilha')

from app.partilha import routes  # noqa: E402, F401
