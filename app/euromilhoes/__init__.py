from flask import Blueprint

euromilhoes = Blueprint('euromilhoes', __name__)

from app.euromilhoes import routes  # noqa: F401, E402
