from flask import Blueprint

bp = Blueprint('conversoes', __name__)

from app.conversoes import routes  # noqa: E402, F401