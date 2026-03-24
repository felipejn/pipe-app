from flask import Blueprint

bp = Blueprint('passwords', __name__)

from app.passwords import routes  # noqa: E402, F401
