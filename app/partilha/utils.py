from functools import wraps

from flask import abort, current_app
from flask_login import current_user

from app import db
from app.auth.models import User
from app.partilha.models import PartilhaRecurso

# Mapeamento do tipo de recurso para o modelo SQLAlchemy correspondente.
MODELOS_RECURSO = {
    'tarefa': 'app.tarefas.models.Tarefa',
    'nota': 'app.notas.models.Nota',
    'evento': 'app.calendario.models.Evento',
}


def _obter_modelo(tipo_recurso):
    """Devolve a classe do modelo para um tipo de recurso, importando preguiçosamente."""
    caminho = MODELOS_RECURSO.get(tipo_recurso)
    if not caminho:
        return None
    modulo_nome, _, classe_nome = caminho.rpartition('.')
    modulo = __import__(modulo_nome, fromlist=[classe_nome])
    return getattr(modulo, classe_nome)


def pode_aceder_recurso(tipo_recurso, recurso_id, utilizador_id, nivel_minimo='leitura'):
    """Devolve True se o utilizador acede ao recurso (dono ou partilhado com nível suficiente).

    Um utilizador acede se:
    - for o dono do recurso (user_id == utilizador_id), ou
    - existir uma partilha estado='aceite' com utilizador_id == utilizador_id e
      nivel >= nivel_minimo (edicao implica leitura).
    """
    modelo = _obter_modelo(tipo_recurso)
    if modelo is None:
        return False

    # Dono tem acesso total (leitura e escrita).
    recurso = modelo.query.filter_by(id=recurso_id, user_id=utilizador_id).first()
    if recurso is not None:
        return True

    # Verificar partilha aceite.
    if nivel_minimo == 'edicao':
        niveis_validos = ('edicao',)  # so edicao permite escrita
    else:
        niveis_validos = ('leitura', 'edicao')

    partilha = PartilhaRecurso.query.filter(
        PartilhaRecurso.tipo_recurso == tipo_recurso,
        PartilhaRecurso.recurso_id == recurso_id,
        PartilhaRecurso.utilizador_id == utilizador_id,
        PartilhaRecurso.estado == 'aceite',
        PartilhaRecurso.nivel.in_(niveis_validos),
    ).first()

    return partilha is not None


def obter_recurso_ou_404(tipo_recurso, recurso_id, utilizador_id, nivel_minimo='leitura'):
    """Devolve o recurso se o utilizador tiver acesso, ou levanta 404."""
    modelo = _obter_modelo(tipo_recurso)
    if modelo is None:
        abort(404)

    # Dono: acesso total.
    recurso = modelo.query.filter_by(id=recurso_id, user_id=utilizador_id).first()
    if recurso is not None:
        return recurso

    # Partilhado: so se houver partilha aceite com nivel suficiente.
    if nivel_minimo == 'edicao':
        niveis_validos = ('edicao',)
    else:
        niveis_validos = ('leitura', 'edicao')

    tem_partilha = db.session.query(PartilhaRecurso).filter(
        PartilhaRecurso.tipo_recurso == tipo_recurso,
        PartilhaRecurso.recurso_id == recurso_id,
        PartilhaRecurso.utilizador_id == utilizador_id,
        PartilhaRecurso.estado == 'aceite',
        PartilhaRecurso.nivel.in_(niveis_validos),
    ).first()

    if tem_partilha is None:
        abort(404)

    return modelo.query.filter_by(id=recurso_id).first()


def requer_acesso_recurso(tipo_recurso, id_param='id', nivel='leitura'):
    """Decorator para rotas que acedem a um recurso partilhado.

    O id do recurso e obtido dos argumentos da view (parametro `id_param` por defeito 'id').
    Se o utilizador nao tiver acesso, devolve 404.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            recurso_id = kwargs.get(id_param)
            if recurso_id is None:
                # Tentar extrair do corpo JSON para PUT/POST.
                from flask import request
                dados = request.get_json(silent=True) or {}
                recurso_id = dados.get('id') or dados.get('recurso_id')
            if not pode_aceder_recurso(tipo_recurso, recurso_id, current_user.id, nivel):
                abort(404)
            return f(*args, **kwargs)
        return wrapper
    return decorator
