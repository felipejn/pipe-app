import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.auth.models import User
from app.combustiveis.models import (
    Posto, PrecoHistorico, UtilizadorCombustivel, UtilizadorConcelho,
)
from app.modulos.config import MODULOS_DISPONIVEIS
from app.poupa_mais.services import calcular_beneficios


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        assert 'memory' in str(db.engine.url)
        db.create_all()
        yield app
        db.session.remove()


@pytest.fixture
def utilizador(app):
    with app.app_context():
        user = User(username='poupa-teste', email='poupa@exemplo.pt')
        user.password_hash = 'hash-teste'
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.mark.parametrize(('litros', 'bp', 'saldo'), [
    (16, 0, 0), (16.01, 2, 1), (19.99, 2, 1),
    (20, 4, 1), (24.99, 4, 1), (25, 5, 1),
    (30, 6, 2), (35, 7, 2), (40, 8, 3),
    (45, 9, 3), (50, 10, 4), (55, 11, 4),
    (60, 12, 6), (100, 12, 6),
])
def test_escaloes_e_limites(litros, bp, saldo):
    resultado = calcular_beneficios(litros)
    assert resultado['bp'] == bp
    assert resultado['saldo'] == saldo
    assert resultado['total'] == bp + saldo
    assert resultado['elegivel'] is (litros > 16)


@pytest.mark.parametrize('litros', [0, 16, 100.01, 120])
def test_fora_da_tabela(litros):
    resultado = calcular_beneficios(litros)
    assert resultado['elegivel'] is False
    assert resultado['bp'] == 0
    assert resultado['saldo'] == 0


def test_loja_regista_modulo_e_endpoint():
    assert MODULOS_DISPONIVEIS['poupa_mais']['url_endpoint'] == 'poupa_mais.index'


def test_simulador_filtra_concelhos_combustiveis_e_postos_e_nao_guarda_historico(app, utilizador):
    with app.app_context():
        db.session.add_all([
            UtilizadorConcelho(user_id=utilizador, concelho='Braga'),
            UtilizadorCombustivel(user_id=utilizador, tipo_combustivel='Gasóleo'),
            UtilizadorCombustivel(user_id=utilizador, tipo_combustivel='Gasolina 95'),
        ])
        bp = Posto(id=1, nome='BP Centro', marca='BP', concelho='Braga', ativo=True)
        pd = Posto(id=2, nome='Pingo Doce Braga', marca=None, concelho='Braga', ativo=True)
        outro = Posto(id=3, nome='BP Porto', marca='BP', concelho='Porto', ativo=True)
        falso_positivo = Posto(id=4, nome='Sub BP Serviços', marca='SubBrand', concelho='Braga', ativo=True)
        db.session.add_all([bp, pd, outro, falso_positivo])
        db.session.add(PrecoHistorico(
            posto_id=1, tipo_combustivel='Gasóleo', preco=1.6,
            data_atualizacao_dgeg='2026-10-01',
        ))
        db.session.add(PrecoHistorico(
            posto_id=1, tipo_combustivel='Gasóleo', preco=1.7,
            data_atualizacao_dgeg='2026-11-01',
        ))
        db.session.commit()
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(utilizador)
            sess['_fresh'] = True

        response = client.get('/poupa-mais/')
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'BP Centro' in html
        assert 'Pingo Doce Braga' in html
        assert 'BP Porto' not in html
        assert 'Sub BP Serviços' not in html
        assert '2026-11-01' in html
        assert 'data-preco="1.7"' in html

        token_response = client.get('/poupa-mais/')
        # CSRF token is available from the page meta tag; the simulator submits via POST.
        from re import search
        token = search(r'<meta name="csrf-token" content="([^"]+)"', token_response.get_data(as_text=True)).group(1)
        sim = client.post('/poupa-mais/', data={
            'posto_combustivel': '1|Gasóleo', 'modo': 'euros', 'quantidade': '40',
            'csrf_token': token,
        })
        sim_html = sim.get_data(as_text=True)
        assert sim.status_code == 200
        assert '1.700' in sim_html
        assert '23,53' in sim_html or '23.53' in sim_html
        assert 'Litros estimados:' in sim_html
        assert 'poupa-contexto' not in sim_html
        assert '4,00' in sim_html or '4.00' in sim_html
        assert '1,00' in sim_html or '1.00' in sim_html
        assert '36,00' in sim_html or '36.00' in sim_html
        assert '1.530' in sim_html
        assert '<option value="1|Gasóleo" selected' in sim_html
        next_page = client.get('/poupa-mais/').get_data(as_text=True)
        assert '<option value="1|Gasóleo" selected' in next_page
        assert PrecoHistorico.query.count() == 2


def test_conversao_e_preco_manual(app, utilizador):
    with app.app_context():
        db.session.add_all([
            UtilizadorConcelho(user_id=utilizador, concelho='Braga'),
            UtilizadorCombustivel(user_id=utilizador, tipo_combustivel='Gasolina 95'),
        ])
        db.session.add(Posto(id=11, nome='BP sem preço', marca='BP', concelho='Braga', ativo=True))
        db.session.commit()
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(utilizador)
            sess['_fresh'] = True
        page = client.get('/poupa-mais/').get_data(as_text=True)
        from re import search
        token = search(r'<meta name="csrf-token" content="([^"]+)"', page).group(1)
        response = client.post('/poupa-mais/', data={
            'posto_combustivel': '11|Gasolina 95', 'modo': 'euros',
            'quantidade': '50', 'preco_manual': '2.00', 'csrf_token': token,
        })
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert '25,00' in html or '25.00' in html
        assert '5,00' in html or '5.00' in html
        assert '45,00' in html or '45.00' in html
        assert '1.800' in html
        assert PrecoHistorico.query.count() == 0
