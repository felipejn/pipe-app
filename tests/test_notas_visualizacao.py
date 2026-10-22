"""Testes da leitura completa de notas e das permissões na checklist."""

import pytest

from app import create_app, db
from app.auth.models import User
from app.notas.models import EtiquetaNota, ItemChecklist, Nota
from app.partilha.models import PartilhaRecurso


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
def utilizadores(app):
    with app.app_context():
        dono = User(username='dono', email='dono@exemplo.com', nome='Dono', apelido='Nota', activo=True)
        leitor = User(username='leitor', email='leitor@exemplo.com', nome='Leitor', apelido='Nota', activo=True)
        editor = User(username='editor', email='editor@exemplo.com', nome='Editor', apelido='Nota', activo=True)
        for utilizador in (dono, leitor, editor):
            utilizador.set_password('senha123')
        db.session.add_all((dono, leitor, editor))
        db.session.commit()
        return {'dono': dono.id, 'leitor': leitor.id, 'editor': editor.id}


@pytest.fixture
def nota_completa(app, utilizadores):
    with app.app_context():
        nota = Nota(
            titulo='Leitura completa', corpo='Primeira linha\n' + ('Conteúdo longo. ' * 30),
            tipo=Nota.TIPO_CHECKLIST, cor='azul', user_id=utilizadores['dono'],
        )
        etiqueta = EtiquetaNota(nome='projecto', user_id=utilizadores['dono'])
        nota.etiquetas.append(etiqueta)
        db.session.add(nota)
        db.session.flush()
        itens = [ItemChecklist(texto=f'Item {i}', ordem=i, feito=i == 0, nota_id=nota.id) for i in range(8)]
        db.session.add_all(itens)
        db.session.add_all([
            PartilhaRecurso(
                tipo_recurso='nota', recurso_id=nota.id, dono_id=utilizadores['dono'],
                utilizador_id=utilizadores['leitor'], nivel='leitura', estado='aceite',
            ),
            PartilhaRecurso(
                tipo_recurso='nota', recurso_id=nota.id, dono_id=utilizadores['dono'],
                utilizador_id=utilizadores['editor'], nivel='edicao', estado='aceite',
            ),
        ])
        db.session.commit()
        return nota.id


def _autenticar(client, utilizador_id):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(utilizador_id)
        sess['_fresh'] = True


def test_dados_de_nota_incluem_corpo_etiquetas_e_todos_os_itens(
    client, utilizadores, nota_completa,
):
    _autenticar(client, utilizadores['dono'])

    resposta = client.get(f'/notas/{nota_completa}/dados')

    assert resposta.status_code == 200
    assert resposta.headers['Cache-Control'] == 'no-store'
    dados = resposta.get_json()
    assert dados['titulo'] == 'Leitura completa'
    assert dados['corpo'].endswith('Conteúdo longo. ' * 30)
    assert dados['etiquetas'] == ['projecto']
    assert len(dados['itens']) == 8
    assert dados['itens'][0]['texto'] == 'Item 0'
    assert dados['itens'][0]['feito'] is True
    assert dados['editavel'] is True


def test_grelha_renderiza_cartoes_que_abrem_a_janela_de_leitura(
    client, utilizadores, nota_completa,
):
    _autenticar(client, utilizadores['dono'])

    resposta = client.get('/notas/')

    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert '<dialog class="nota-visualizar-dialog"' in html
    assert 'role="group"' in html
    assert 'data-nota-dados="/notas/1/dados"' in html


def test_nota_partilhada_em_leitura_pode_ser_lida_sem_permitir_edicao(
    client, utilizadores, nota_completa,
):
    _autenticar(client, utilizadores['leitor'])

    resposta = client.get(f'/notas/{nota_completa}/dados')

    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados['titulo'] == 'Leitura completa'
    assert dados['editavel'] is False


def test_utilizador_sem_acesso_nao_obtem_dados_da_nota(client, nota_completa):
    resposta = client.get(f'/notas/{nota_completa}/dados')

    assert resposta.status_code == 302


def test_leitor_partilhado_nao_pode_alterar_item_da_checklist(
    app, client, utilizadores, nota_completa,
):
    _autenticar(client, utilizadores['leitor'])
    with app.app_context():
        item_id = ItemChecklist.query.filter_by(nota_id=nota_completa).first().id

    resposta = client.post(
        f'/notas/{nota_completa}/accao',
        json={'accao': 'toggle_item', 'item_id': item_id},
    )

    assert resposta.status_code == 404
    with app.app_context():
        assert db.session.get(ItemChecklist, item_id).feito is True


def test_editor_partilhado_pode_alterar_item_da_checklist(
    app, client, utilizadores, nota_completa,
):
    _autenticar(client, utilizadores['editor'])
    with app.app_context():
        item_id = ItemChecklist.query.filter_by(nota_id=nota_completa).first().id

    resposta = client.post(
        f'/notas/{nota_completa}/accao',
        json={'accao': 'toggle_item', 'item_id': item_id},
    )

    assert resposta.status_code == 200
    with app.app_context():
        assert db.session.get(ItemChecklist, item_id).feito is False
