from flask import Blueprint

tarefas = Blueprint('tarefas', __name__)

from app.tarefas import routes  # noqa: F401, E402
