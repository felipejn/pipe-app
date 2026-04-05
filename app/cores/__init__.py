from flask import Blueprint

bp = Blueprint('cores', __name__)

from app.cores import routes  # noqa: E402, F401
