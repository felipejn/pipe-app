"""Regressões de autorização da Loja de Módulos."""

from app import create_app, db
from app.auth.models import User
from app.modulos.models import UserModulo


def test_toggle_ignora_user_id_enviado_pelo_browser():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        utilizador = User(
            username='loja-a', email='loja-a@example.test', password_hash='x')
        outro = User(
            username='loja-b', email='loja-b@example.test', password_hash='x')
        db.session.add_all([utilizador, outro])
        db.session.flush()
        db.session.add(UserModulo(
            user_id=outro.id, modulo_slug='calendario', ativo=True))
        db.session.commit()
        utilizador_id, outro_id = utilizador.id, outro.id

    cliente = app.test_client()
    with cliente.session_transaction() as sess:
        sess['_user_id'] = utilizador_id
        sess['_fresh'] = True

    resposta = cliente.post('/modulos/api/toggle', json={
        'modulo_slug': 'calendario',
        'user_id': outro_id,
        'ativo': False,
    })

    assert resposta.status_code == 200
    with app.app_context():
        assert UserModulo.query.filter_by(
            user_id=outro_id, modulo_slug='calendario').one().ativo is True
        assert UserModulo.query.filter_by(
            user_id=utilizador_id, modulo_slug='calendario').one().ativo is False
        db.session.remove()
        db.drop_all()
