"""Testes da funcionalidade de partilha de recursos entre utilizadores.

Cobertura: criacao de partilha (por email), aceitacao, acesso a recurso
partilhado, necao de acesso a nao-partilhados, nivel de edicao vs leitura,
listagem de partilhados comigo, remocao de partilha, partilha consigo mesmo
e email inexistente.
"""

import pytest

from app import create_app, db
from app.auth.models import User
from app.tarefas.models import Lista, Tarefa
from app.notas.models import Nota
from app.calendario.models import Evento
from app.partilha.models import PartilhaRecurso
from datetime import datetime, timedelta


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def utilizador_a(app):
    with app.app_context():
        u = User(username='a', email='a@exemplo.com', nome='A', apelido='Utilizador', activo=True)
        u.set_password('senha123')
        db.session.add(u)
        db.session.commit()
        return {'id': u.id, 'email': u.email}


@pytest.fixture
def utilizador_b(app):
    with app.app_context():
        u = User(username='b', email='b@exemplo.com', nome='B', apelido='Utilizador', activo=True)
        u.set_password('senha123')
        db.session.add(u)
        db.session.commit()
        return {'id': u.id, 'email': u.email}


@pytest.fixture
def utilizador_c(app):
    with app.app_context():
        u = User(username='c', email='c@exemplo.com', nome='C', apelido='Utilizador', activo=True)
        u.set_password('senha123')
        db.session.add(u)
        db.session.commit()
        return {'id': u.id, 'email': u.email}


def _login(client, email, password='senha123'):
    client.get('/auth/logout')  # garantir sessão limpa
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=False)


def _criar_tarefa(app, user_id, texto='Minha tarefa'):
    with app.app_context():
        lista = Lista(nome='Lista teste', user_id=user_id)
        db.session.add(lista)
        db.session.commit()
        t = Tarefa(texto=texto, prioridade='media', lista_id=lista.id, user_id=user_id)
        db.session.add(t)
        db.session.commit()
        return t.id


def _criar_nota(app, user_id, titulo='Minha nota'):
    with app.app_context():
        n = Nota(titulo=titulo, corpo='corpo', tipo='texto', user_id=user_id)
        db.session.add(n)
        db.session.commit()
        return n.id


def _criar_evento(app, user_id, titulo='Meu evento'):
    with app.app_context():
        inicio = datetime.utcnow()
        fim = inicio + timedelta(hours=1)
        e = Evento(
            user_id=user_id, titulo=titulo, descricao='d',
            data_inicio=inicio, data_fim=fim, dia_inteiro=False, cor='tomate', notificar=True,
        )
        db.session.add(e)
        db.session.commit()
        return e.id


# ── Caso 1: criar partilha (A cria recurso, A partilha com B via email) ──────

def test_criar_partilha_por_email(app, client, utilizador_a, utilizador_b):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_tarefa(app, utilizador_a['id'])

    resp = client.post(
        f'/partilha/tarefa/{recurso_id}',
        json={'email': utilizador_b['email'], 'nivel': 'leitura'},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['estado'] == 'pendente'
    assert data['nivel'] == 'leitura'
    assert data['utilizador_email'] == utilizador_b['email']

    with app.app_context():
        partilha = PartilhaRecurso.query.filter_by(
            tipo_recurso='tarefa', recurso_id=recurso_id, utilizador_id=utilizador_b['id'],
        ).first()
        assert partilha is not None
        assert partilha.dono_id == utilizador_a['id']
        assert partilha.estado == 'pendente'


# ── Caso 2: aceitar partilha ─────────────────────────────────────────────────

def test_aceitar_partilha(app, client, utilizador_a, utilizador_b):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_tarefa(app, utilizador_a['id'])
    client.post(
        f'/partilha/tarefa/{recurso_id}',
        json={'email': utilizador_b['email'], 'nivel': 'leitura'},
    )

    with app.app_context():
        partilha = PartilhaRecurso.query.filter_by(
            tipo_recurso='tarefa', recurso_id=recurso_id, utilizador_id=utilizador_b['id'],
        ).first()
        partilha_id = partilha.id

    _login(client, utilizador_b['email'])
    resp = client.post(f'/partilha/{partilha_id}/aceitar')
    assert resp.status_code == 200
    assert resp.get_json()['estado'] == 'aceite'

    with app.app_context():
        p = PartilhaRecurso.query.get(partilha_id)
        assert p.estado == 'aceite'


# ── Caso 3: aceder recurso partilhado (B le o recurso sem ser dono) ──────────

def test_aceder_recurso_partilhado(app, client, utilizador_a, utilizador_b):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_tarefa(app, utilizador_a['id'])
    client.post(
        f'/partilha/tarefa/{recurso_id}',
        json={'email': utilizador_b['email'], 'nivel': 'leitura'},
    )

    # B aceita
    with app.app_context():
        partilha_id = PartilhaRecurso.query.filter_by(
            tipo_recurso='tarefa', recurso_id=recurso_id, utilizador_id=utilizador_b['id'],
        ).first().id
    _login(client, utilizador_b['email'])
    client.post(f'/partilha/{partilha_id}/aceitar')

    # B tenta ler a tarefa (via edicao, que exige 'edicao' -> 404 para leitura)
    resp = client.post(f'/tarefas/{recurso_id}/toggle')
    assert resp.status_code == 404  # B so tem leitura, nao pode editar

    # Listar partilhados comigo deve conter a tarefa
    resp = client.get('/partilha/minhas')
    assert resp.status_code == 200
    titulos = [r['titulo'] for r in resp.get_json()]
    assert any('Minha tarefa' in t for t in titulos)


# ── Caso 4: negar acesso a nao-partilhado (C recebe 404) ────────────────────

def test_nao_partilhado_recebe_404(app, client, utilizador_a, utilizador_c):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_tarefa(app, utilizador_a['id'])
    # Nao partilha com C

    _login(client, utilizador_c['email'])
    resp = client.post(f'/tarefas/{recurso_id}/toggle')
    assert resp.status_code == 404


# ── Caso 5: nivel edicao (B com 'edicao' modifica; 'leitura' recebe 404) ─────

def test_nivel_edicao_permite_modificar(app, client, utilizador_a, utilizador_b):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_nota(app, utilizador_a['id'])
    client.post(
        f'/partilha/nota/{recurso_id}',
        json={'email': utilizador_b['email'], 'nivel': 'edicao'},
    )
    with app.app_context():
        partilha_id = PartilhaRecurso.query.filter_by(
            tipo_recurso='nota', recurso_id=recurso_id, utilizador_id=utilizador_b['id'],
        ).first().id
    _login(client, utilizador_b['email'])
    client.post(f'/partilha/{partilha_id}/aceitar')

    # B com edicao consegue editar a nota (redirect 302 em caso de sucesso)
    resp = client.post(f'/notas/{recurso_id}', data={'titulo': 'Titulo alterado', 'corpo': 'x', 'cor': 'padrao', 'etiquetas': ''})
    assert resp.status_code == 302


def test_nivel_leitura_nao_permite_editar(app, client, utilizador_a, utilizador_b):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_nota(app, utilizador_a['id'])
    client.post(
        f'/partilha/nota/{recurso_id}',
        json={'email': utilizador_b['email'], 'nivel': 'leitura'},
    )
    with app.app_context():
        partilha_id = PartilhaRecurso.query.filter_by(
            tipo_recurso='nota', recurso_id=recurso_id, utilizador_id=utilizador_b['id'],
        ).first().id
    _login(client, utilizador_b['email'])
    client.post(f'/partilha/{partilha_id}/aceitar')

    # B so tem leitura -> edicao deve falhar com 404
    resp = client.post(f'/notas/{recurso_id}', data={'titulo': 'X', 'corpo': 'x', 'cor': 'padrao', 'etiquetas': ''})
    assert resp.status_code == 404


# ── Caso 6: listar partilhados comigo ────────────────────────────────────────

def test_listar_partilhadas_comigo(app, client, utilizador_a, utilizador_b):
    _login(client, utilizador_a['email'])
    _criar_tarefa(app, utilizador_a['id'])
    _criar_nota(app, utilizador_a['id'])
    _criar_evento(app, utilizador_a['id'])

    # Partilhar os 3 com B
    for tipo, rid in [('tarefa', 1), ('nota', 2), ('evento', 3)]:
        pass  # ids reais abaixo

    with app.app_context():
        tarefa_id = Tarefa.query.filter_by(user_id=utilizador_a['id']).first().id
        nota_id = Nota.query.filter_by(user_id=utilizador_a['id']).first().id
        evento_id = Evento.query.filter_by(user_id=utilizador_a['id']).first().id

    client.post(f'/partilha/tarefa/{tarefa_id}', json={'email': utilizador_b['email'], 'nivel': 'leitura'})
    client.post(f'/partilha/nota/{nota_id}', json={'email': utilizador_b['email'], 'nivel': 'leitura'})
    client.post(f'/partilha/evento/{evento_id}', json={'email': utilizador_b['email'], 'nivel': 'leitura'})

    # B aceita todas
    with app.app_context():
        ids = [p.id for p in PartilhaRecurso.query.filter_by(utilizador_id=utilizador_b['id'], estado='pendente').all()]
    _login(client, utilizador_b['email'])
    for pid in ids:
        client.post(f'/partilha/{pid}/aceitar')

    resp = client.get('/partilha/minhas')
    assert resp.status_code == 200
    dados = resp.get_json()
    tipos = {r['tipo_recurso'] for r in dados}
    assert 'tarefa' in tipos
    assert 'nota' in tipos
    assert 'evento' in tipos


# ── Caso 7: remover partilha (A cancela; B deixa de aceder) ──────────────────

def test_remover_partilha_bloqueia_acesso(app, client, utilizador_a, utilizador_b):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_tarefa(app, utilizador_a['id'])
    client.post(
        f'/partilha/tarefa/{recurso_id}',
        json={'email': utilizador_b['email'], 'nivel': 'edicao'},
    )
    with app.app_context():
        partilha_id = PartilhaRecurso.query.filter_by(
            tipo_recurso='tarefa', recurso_id=recurso_id, utilizador_id=utilizador_b['id'],
        ).first().id
    _login(client, utilizador_b['email'])
    client.post(f'/partilha/{partilha_id}/aceitar')

    # A remove a partilha
    _login(client, utilizador_a['email'])
    resp = client.delete(f'/partilha/{partilha_id}')
    assert resp.status_code == 200

    # B (re-login) nao consegue mais editar
    _login(client, utilizador_b['email'])
    resp = client.post(f'/tarefas/{recurso_id}/toggle')
    assert resp.status_code == 404


# ── Caso 8: nao se partilhar consigo mesmo ────────────────────────────────────

def test_nao_partilhar_consigo_mesmo(app, client, utilizador_a):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_tarefa(app, utilizador_a['id'])

    resp = client.post(
        f'/partilha/tarefa/{recurso_id}',
        json={'email': utilizador_a['email'], 'nivel': 'leitura'},
    )
    assert resp.status_code == 400
    assert 'consigo mesmo' in resp.get_json()['erro']


# ── Caso 9: email inexistente ────────────────────────────────────────────────

def test_email_inexistente(app, client, utilizador_a):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_tarefa(app, utilizador_a['id'])

    resp = client.post(
        f'/partilha/tarefa/{recurso_id}',
        json={'email': 'naoexiste@exemplo.com', 'nivel': 'leitura'},
    )
    assert resp.status_code == 404
    assert 'Nao existe utilizador registado' in resp.get_json()['erro']


# ── Caso 10: email vazio ─────────────────────────────────────────────────────

def test_email_vazio(app, client, utilizador_a):
    _login(client, utilizador_a['email'])
    recurso_id = _criar_tarefa(app, utilizador_a['id'])

    resp = client.post(
        f'/partilha/tarefa/{recurso_id}',
        json={'nivel': 'leitura'},
    )
    assert resp.status_code == 400
