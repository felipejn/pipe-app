from flask import Blueprint

bp = Blueprint('poupa_mais', __name__, url_prefix='/poupa-mais')

from app.poupa_mais import routes  # noqa: E402,F401
