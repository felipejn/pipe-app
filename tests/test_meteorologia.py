"""Testes da Etapa A — Localizacao (modulo Meteorologia)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db  # noqa: E402


@pytest.fixture
def app():
    app = create_app('testing')
    app.config['OPENWEATHER_API_KEY'] = 'test-chave-testes'
    with app.app_context():
        uri = str(db.engine.url)
        assert 'memory' in uri, f'ABORTADO: BD real ({uri}).'
        db.create_all()
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    from werkzeug.security import generate_password_hash
    from app.auth.models import User
    with client.application.app_context():
        user = User(username='meteouser', email='meteouser@example.com')
        user.password_hash = generate_password_hash('testpass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    with client.session_transaction() as sess:
        sess['_user_id'] = user_id
    return client


@pytest.fixture
def outro_user_id(app):
    """Id de um segundo utilizador (sem cliente proprio)."""
    from werkzeug.security import generate_password_hash
    from app.auth.models import User
    with app.app_context():
        user = User(username='meteoutro', email='meteoutro@example.com')
        user.password_hash = generate_password_hash('testpass123')
        db.session.add(user)
        db.session.commit()
        return user.id


class TestLoginObrigatorio:
    def test_pagina_localizacao_anonima_redireciona(self, client):
        resposta = client.get('/meteorologia/localizacao')
        assert resposta.status_code == 302
        assert '/auth/login' in resposta.headers['Location']

    def test_pesquisar_anonimo_redireciona(self, client):
        resposta = client.get('/meteorologia/api/pesquisar?q=Braga')
        assert resposta.status_code == 302

    def test_guardar_anonimo_redireciona(self, client):
        resposta = client.post('/meteorologia/api/localizacao', json={})
        assert resposta.status_code == 302

class TestPaginaLocalizacao:
    def test_pagina_abre_sem_local(self, authenticated_client):
        resposta = authenticated_client.get('/meteorologia/localizacao')
        assert resposta.status_code == 200
        assert 'Definir'.encode('utf-8') in resposta.data

    def test_pagina_mostra_local_guardada(self, authenticated_client):
        payload = {
            'nome': 'Vila Verde', 'latitude': 41.65,
            'longitude': -8.43, 'pais': 'Portugal',
            'regiao': 'Distrito de Braga', 'timezone': 'Europe/Lisbon',
        }
        r = authenticated_client.post('/meteorologia/api/localizacao', json=payload)
        assert r.status_code == 200
        resposta = authenticated_client.get('/meteorologia/localizacao')
        assert resposta.status_code == 200
        assert b'Vila Verde' in resposta.data


class _RespostaFalsa:
    def __init__(self, dados):
        self._dados = dados
    def raise_for_status(self):
        return None
    def json(self):
        return self._dados


GEOCODING_VILA_VERDE = [
    {'name': 'Vila Verde', 'local_names': {'pt': 'Vila Verde'},
     'lat': 41.65, 'lon': -8.43, 'country': 'PT', 'state': 'Braga'},
    {'name': 'Vila Verde', 'lat': 39.0, 'lon': -9.0,
     'country': 'PT', 'state': 'Lisboa'},
]


def _mock_get_vila_verde(monkeypatch):
    import app.meteorologia.services as servicos
    def falso_get(url, params=None, timeout=None, headers=None):
        assert params['q'] == 'Vila Verde'
        assert params['limit'] == 5
        assert params['appid'] == 'test-chave-testes'
        return _RespostaFalsa(GEOCODING_VILA_VERDE)
    monkeypatch.setattr(servicos.requests, 'get', falso_get)


class TestPesquisar:
    def test_q_vazio_devolve_400(self, authenticated_client):
        r = authenticated_client.get('/meteorologia/api/pesquisar?q=')
        assert r.status_code == 400

    def test_q_em_falta_devolve_400(self, authenticated_client):
        r = authenticated_client.get('/meteorologia/api/pesquisar')
        assert r.status_code == 400

    def test_pesquisa_valida_normaliza(self, authenticated_client, monkeypatch):
        _mock_get_vila_verde(monkeypatch)
        r = authenticated_client.get('/meteorologia/api/pesquisar?q=Vila Verde')
        assert r.status_code == 200
        resultados = r.get_json()['resultados']
        assert len(resultados) == 2
        primeiro, segundo = resultados
        assert primeiro['nome'] == 'Vila Verde'
        assert primeiro['pais'] == 'Portugal'
        assert primeiro['regiao'] == 'Braga'
        assert primeiro['detalhe'] is None
        assert primeiro['latitude'] == 41.65
        assert segundo['detalhe'] is None

    def test_sem_results_devolve_vazio(self, authenticated_client, monkeypatch):
        import app.meteorologia.services as servicos
        monkeypatch.setattr(
            servicos.requests, 'get', lambda *a, **k: _RespostaFalsa({}))
        r = authenticated_client.get('/meteorologia/api/pesquisar?q=XyzNada')
        assert r.status_code == 200
        assert r.get_json() == {'resultados': []}

    def test_timeout_devolve_503(self, authenticated_client, monkeypatch):
        import requests
        import app.meteorologia.services as servicos
        def rebentar(*a, **k):
            raise requests.Timeout('esgotado')
        monkeypatch.setattr(servicos.requests, 'get', rebentar)
        r = authenticated_client.get('/meteorologia/api/pesquisar?q=Braga')
        assert r.status_code == 503
        assert 'erro' in r.get_json()

class TestGuardar:
    def test_gravacao_valida_cria_linha(self, authenticated_client):
        from app.meteorologia.models import LocalizacaoMeteorologia
        payload = {
            'nome': 'Vila Verde', 'latitude': 41.65,
            'longitude': -8.43, 'pais': 'Portugal',
            'regiao': 'Distrito de Braga', 'timezone': 'Europe/Lisbon',
        }
        r = authenticated_client.post('/meteorologia/api/localizacao', json=payload)
        assert r.status_code == 200
        assert r.get_json() == {'ok': True}
        with authenticated_client.application.app_context():
            linhas = LocalizacaoMeteorologia.query.all()
            assert len(linhas) == 1
            assert linhas[0].nome == 'Vila Verde'
            assert linhas[0].timezone == 'Europe/Lisbon'

    def test_lat_invalida_400_sem_gravar(self, authenticated_client):
        from app.meteorologia.models import LocalizacaoMeteorologia
        payload = {'nome': 'X', 'latitude': 999,
                   'longitude': -8.43, 'pais': 'Portugal'}
        r = authenticated_client.post('/meteorologia/api/localizacao', json=payload)
        assert r.status_code == 400
        with authenticated_client.application.app_context():
            assert LocalizacaoMeteorologia.query.count() == 0

    def test_tipos_errados_400(self, authenticated_client):
        from app.meteorologia.models import LocalizacaoMeteorologia
        payload = {'nome': 'Vila Verde', 'latitude': 'norte',
                   'longitude': -8.43, 'pais': 'Portugal'}
        r = authenticated_client.post('/meteorologia/api/localizacao', json=payload)
        assert r.status_code == 400
        with authenticated_client.application.app_context():
            assert LocalizacaoMeteorologia.query.count() == 0

    def test_regravacao_faz_update(self, authenticated_client):
        from app.meteorologia.models import LocalizacaoMeteorologia
        p1 = {'nome': 'Vila Verde', 'latitude': 41.65,
              'longitude': -8.43, 'pais': 'Portugal'}
        p2 = {'nome': 'Braga', 'latitude': 41.55,
              'longitude': -8.42, 'pais': 'Portugal'}
        assert authenticated_client.post(
            '/meteorologia/api/localizacao', json=p1).status_code == 200
        assert authenticated_client.post(
            '/meteorologia/api/localizacao', json=p2).status_code == 200
        with authenticated_client.application.app_context():
            linhas = LocalizacaoMeteorologia.query.all()
            assert len(linhas) == 1
            assert linhas[0].nome == 'Braga'

    def test_isolamento_utilizadores(self, authenticated_client, outro_user_id):
        from app.meteorologia.models import LocalizacaoMeteorologia
        from app.meteorologia import services as servicos
        payload = {'nome': 'Vila Verde', 'latitude': 41.65,
                   'longitude': -8.43, 'pais': 'Portugal'}
        assert authenticated_client.post(
            '/meteorologia/api/localizacao', json=payload).status_code == 200
        # O outro utilizador nao tem localizacao: a query filtrada por
        # user_id devolve None e a BD mantem uma so linha do primeiro.
        with authenticated_client.application.app_context():
            assert LocalizacaoMeteorologia.query.filter_by(
                user_id=outro_user_id).first() is None
            assert LocalizacaoMeteorologia.query.count() == 1
            # E o servico guarda por user_id sem tocar na linha alheia.
            ok, erro = servicos.guardar_localizacao(
                outro_user_id, dict(payload, nome='Braga'))
            assert ok, erro
            assert LocalizacaoMeteorologia.query.count() == 2
            nomes = {l.nome for l in LocalizacaoMeteorologia.query.all()}
            assert nomes == {'Vila Verde', 'Braga'}


class TestRegistoModulo:
    def test_slug_na_loja(self):
        from app.modulos.config import MODULOS_DISPONIVEIS
        assert 'meteorologia' in MODULOS_DISPONIVEIS
        assert MODULOS_DISPONIVEIS['meteorologia']['url_endpoint'] == 'meteorologia.index'

    def test_toggle_loja(self, authenticated_client):
        from app.auth.models import User
        with authenticated_client.application.app_context():
            user_id = User.query.filter_by(username='meteouser').first().id
        r = authenticated_client.post(
            '/modulos/api/toggle',
            json={'modulo_slug': 'meteorologia',
                  'user_id': user_id, 'activo': True})
        assert r.status_code == 200
        assert r.get_json()['slug'] == 'meteorologia'



# ── Etapa B — Previsão ──


class _RespostaForecast:
    def __init__(self, dados):
        self._dados = dados

    def raise_for_status(self):
        return None

    def json(self):
        return self._dados


def _tempo_atual_valido():
    from calendar import timegm
    from datetime import datetime, timezone
    return {
        'dt': timegm(datetime(2026, 10, 7, 13, tzinfo=timezone.utc).timetuple()),
        'timezone': 3600,
        'main': {'temp': 21.5, 'feels_like': 22.3, 'humidity': 60,
                 'temp_max': 24.0, 'temp_min': 14.0},
        'weather': [{'id': 802, 'description': 'scattered clouds'}],
        'wind': {'speed': 3.47, 'deg': 90},
        'rain': {'1h': 0.0},
    }


def _forecast_valido():
    from calendar import timegm
    from datetime import datetime, timedelta, timezone
    offset = 3600
    base_local = datetime(2026, 10, 7)
    lista = []
    codigos = [802, 804, 500, 800, 211]
    for i in range(40):
        local = base_local + timedelta(hours=3 * i)
        utc = local - timedelta(seconds=offset)
        lista.append({
            'dt': timegm(utc.replace(tzinfo=timezone.utc).timetuple()),
            'dt_txt': local.strftime('%Y-%m-%d %H:%M:%S'),
            'main': {'temp': 10.0 + i * 0.1},
            'weather': [{'id': codigos[i // 8], 'description': 'condição'}],
            'pop': 0.42 if i == 5 else 0.05,
            'rain': {'3h': 1.2 if i == 8 else 0.0},
            'wind': {'speed': 3.0, 'deg': 90},
        })
    return {'city': {'timezone': offset}, 'list': lista}


def _mock_forecast(monkeypatch, dados=None, captar=None):
    import app.meteorologia.services as servicos
    forecast = dados if dados is not None else _forecast_valido()
    atual = _tempo_atual_valido()

    def falso_get(url, params=None, timeout=None, headers=None):
        if captar is not None:
            captar.setdefault(url, []).append(params or {})
        assert params.get('appid')
        if url == servicos.WEATHER_URL:
            return _RespostaForecast(atual)
        assert url == servicos.FORECAST_5DAY_URL
        return _RespostaForecast(forecast)

    monkeypatch.setattr(servicos.requests, 'get', falso_get)



class TestObterPrevisao:
    def test_resposta_valida_normaliza_12_campos(self, monkeypatch):
        from app.meteorologia import services as servicos
        _mock_forecast(monkeypatch)
        previsao = servicos.obter_previsao(41.65, -8.43)
        assert previsao is not None
        atual = previsao['atual']
        assert atual['hora'] == '2026-10-07T14:00'
        assert atual['temperatura'] == 21.5
        assert atual['sensacao_termica'] == 22.3
        assert atual['humidade'] == 60
        assert atual['precipitacao'] == 0.0
        assert atual['probabilidade_precipitacao'] == 42
        assert atual['codigo_wmo'] == 802
        assert atual['vento_velocidade'] == 12
        assert atual['vento_direcao_graus'] == 90
        assert atual['uv'] is None
        assert atual['temp_max_hoje'] == 10.7
        assert atual['temp_min_hoje'] == 10.0

    def test_campos_derivados(self, monkeypatch):
        from app.meteorologia import services as servicos
        _mock_forecast(monkeypatch)
        atual = servicos.obter_previsao(41.65, -8.43)['atual']
        assert atual['descricao_pt'] == 'Nuvens dispersas'
        assert atual['emoji'] == '⛅'
        assert atual['vento_direcao_cardinal'] == 'Este'

    def test_timezone_fonte_horaria_diaria(self, monkeypatch):
        from app.meteorologia import services as servicos
        captar = {}
        _mock_forecast(monkeypatch, captar=captar)
        previsao = servicos.obter_previsao(41.65, -8.43)
        assert previsao['timezone'] == 'UTC+01:00'
        assert previsao['fonte'] == 'OpenWeather'
        assert len(captar[servicos.WEATHER_URL]) == 1
        assert len(captar[servicos.FORECAST_5DAY_URL]) == 1
        assert captar[servicos.WEATHER_URL][0]['units'] == 'metric'
        assert captar[servicos.FORECAST_5DAY_URL][0]['units'] == 'metric'
        assert len(previsao['horaria']) <= 8
        assert previsao['horaria'][0]['hora'] == '2026-10-07T15:00'
        assert previsao['horaria'][0]['prob_precipitacao'] == 42
        assert previsao['horaria'][0]['precipitacao'] == 0.0
        assert len(previsao['diaria']) == 5
        assert previsao['diaria'][0]['temp_max'] == 10.7
        assert previsao['diaria'][0]['temp_min'] == 10.0
        assert previsao['diaria'][2]['codigo_wmo'] == 500
        assert previsao['diaria'][1]['precipitacao'] == 1.2

    def test_lat_lon_invalidos_devolve_none(self):
        from app.meteorologia import services as servicos
        assert servicos.obter_previsao('norte', -8.43) is None
        assert servicos.obter_previsao(999, -8.43) is None
        assert servicos.obter_previsao(41.65, None) is None

    def test_timeout_devolve_none(self, monkeypatch):
        import requests
        import app.meteorologia.services as servicos

        def rebentar(*a, **k):
            raise requests.Timeout('esgotado')

        monkeypatch.setattr(servicos.requests, 'get', rebentar)
        assert servicos.obter_previsao(41.65, -8.43) is None

    def test_erro_http_devolve_none(self, monkeypatch):
        import requests
        import app.meteorologia.services as servicos

        def falhar(*a, **k):
            raise requests.HTTPError('500')

        monkeypatch.setattr(servicos.requests, 'get', falhar)
        assert servicos.obter_previsao(41.65, -8.43) is None

    def test_falha_no_forecast_nao_devolve_temperatura_parcial(self, monkeypatch):
        import requests
        import app.meteorologia.services as servicos
        chamadas = []

        def get(url, **kwargs):
            chamadas.append(url)
            if url == servicos.WEATHER_URL:
                return _RespostaForecast(_tempo_atual_valido())
            raise requests.Timeout('forecast indisponível')

        monkeypatch.setattr(servicos.requests, 'get', get)
        assert servicos.obter_previsao(41.65, -8.43) is None
        assert chamadas == [servicos.WEATHER_URL, servicos.FORECAST_5DAY_URL]

    def test_sem_chave_nao_faz_pedido(self, app, monkeypatch):
        from flask import current_app
        import app.meteorologia.services as servicos
        monkeypatch.delenv('OPENWEATHER_API_KEY', raising=False)
        monkeypatch.setitem(current_app.config, 'OPENWEATHER_API_KEY', '')
        monkeypatch.setattr(
            servicos.requests, 'get',
            lambda *args, **kwargs: pytest.fail('não devia chamar a API'))
        assert servicos.obter_previsao(41.65, -8.43) is None

    def test_sem_current_devolve_none(self, monkeypatch):
        from app.meteorologia import services as servicos
        _mock_forecast(monkeypatch, dados={'timezone': 'x'})
        assert servicos.obter_previsao(41.65, -8.43) is None

    def test_campos_em_falta_dao_none_sem_quebrar(self, monkeypatch):
        from app.meteorologia import services as servicos
        _mock_forecast(monkeypatch)
        previsao = servicos.obter_previsao(41.65, -8.43)
        assert previsao is not None
        assert previsao['atual']['uv'] is None
        assert previsao['atual']['sensacao_termica'] == 22.3


class TestWmoEVento:
    def test_wmo_conhecidos(self):
        from app.meteorologia.services import descrever_wmo
        assert descrever_wmo(0) == ('Céu limpo', '☀️')
        assert descrever_wmo(3) == ('Encoberto', '☁️')
        assert descrever_wmo(61) == ('Chuva fraca', '🌦️')
        assert descrever_wmo(95) == ('Trovoada', '⛈️')

    def test_wmo_desconhecido_e_none(self):
        from app.meteorologia.services import descrever_wmo
        assert descrever_wmo(12345) == ('—', '❔')
        assert descrever_wmo(None) == ('—', '❔')

    def test_vento_cardinal(self):
        from app.meteorologia.services import direcao_cardinal
        assert direcao_cardinal(0) == 'Norte'
        assert direcao_cardinal(90) == 'Este'
        assert direcao_cardinal(180) == 'Sul'
        assert direcao_cardinal(270) == 'Oeste'
        assert direcao_cardinal(45) == 'Nordeste'
        assert direcao_cardinal(None) == '—'
        assert direcao_cardinal('x') == '—'

    def test_codigos_openweather_conhecidos(self):
        from app.meteorologia.services import descrever_openweather
        assert descrever_openweather(800)[0] == 'Céu limpo'
        assert descrever_openweather(802)[0] == 'Nuvens dispersas'
        assert descrever_openweather(500)[0] == 'Chuva fraca'
        assert descrever_openweather(211)[0] == 'Trovoada'


class TestObterPrevisaoUtilizador:
    def test_sem_localizacao(self, authenticated_client):
        from app.meteorologia import services as servicos
        from app.auth.models import User
        with authenticated_client.application.app_context():
            uid = User.query.filter_by(username='meteouser').first().id
            payload, motivo = servicos.obter_previsao_utilizador(uid)
            assert payload is None
            assert motivo == 'sem_localizacao'

    def test_api_indisponivel(self, authenticated_client, monkeypatch):
        import requests
        import app.meteorologia.services as servicos
        from app.auth.models import User

        def rebentar(*a, **k):
            raise requests.Timeout('esgotado')

        monkeypatch.setattr(servicos.requests, 'get', rebentar)
        with authenticated_client.application.app_context():
            uid = User.query.filter_by(username='meteouser').first().id
            ok, _ = servicos.guardar_localizacao(uid, {
                'nome': 'Vila Verde', 'latitude': 41.65,
                'longitude': -8.43, 'pais': 'Portugal'})
            assert ok
            payload, motivo = servicos.obter_previsao_utilizador(uid)
            assert payload is None
            assert motivo == 'api_indisponivel'

    def test_com_localizacao_ok(self, authenticated_client, monkeypatch):
        import app.meteorologia.services as servicos
        from app.auth.models import User
        _mock_forecast(monkeypatch)
        with authenticated_client.application.app_context():
            uid = User.query.filter_by(username='meteouser').first().id
            ok, _ = servicos.guardar_localizacao(uid, {
                'nome': 'Vila Verde', 'latitude': 41.65,
                'longitude': -8.43, 'pais': 'Portugal'})
            assert ok
            payload, motivo = servicos.obter_previsao_utilizador(uid)
            assert motivo == 'ok'
            assert payload['atual']['temperatura'] == 21.5


class TestPaginaPrevisao:
    def test_anonimo_redireciona(self, client):
        resposta = client.get('/meteorologia/')
        assert resposta.status_code == 302
        assert '/auth/login' in resposta.headers['Location']

    def test_sem_local_mostra_estado_vazio(self, authenticated_client):
        resposta = authenticated_client.get('/meteorologia/')
        assert resposta.status_code == 200
        assert 'Definir'.encode('utf-8') in resposta.data
        assert b'/meteorologia/localizacao' in resposta.data

    def test_com_local_mostra_previsao(
            self, authenticated_client, monkeypatch):
        dados = _forecast_valido()
        dados['list'][5]['rain']['3h'] = 0.4
        _mock_forecast(monkeypatch, dados=dados)
        r = authenticated_client.post('/meteorologia/api/localizacao', json={
            'nome': 'Vila Verde', 'latitude': 41.65,
            'longitude': -8.43, 'pais': 'Portugal',
            'regiao': 'Distrito de Braga'})
        assert r.status_code == 200
        resposta = authenticated_client.get('/meteorologia/')
        assert resposta.status_code == 200
        corpo = resposta.data.decode('utf-8')
        assert 'Vila Verde' in corpo
        assert '22 °C' in corpo
        assert '21,5 °C' not in corpo and '21.5 °C' not in corpo
        assert '22,3 °C' not in corpo and '22.3 °C' not in corpo
        assert '11 °C' in corpo
        assert '10 °C' in corpo
        assert '0,4 mm' in corpo or '0.4 mm' in corpo
        assert 'Mudar' in corpo
        assert corpo.index('Mín hoje') < corpo.index('Máx hoje')

    def test_cache_antiga_sem_volume_horario_mostra_traco(
            self, authenticated_client, monkeypatch):
        from app.meteorologia import services as servicos
        _mock_forecast(monkeypatch)
        r = authenticated_client.post('/meteorologia/api/localizacao', json={
            'nome': 'Vila Verde', 'latitude': 41.65,
            'longitude': -8.43, 'pais': 'Portugal'})
        assert r.status_code == 200

        payload_antigo = servicos.obter_previsao(41.65, -8.43)
        for hora in payload_antigo['horaria']:
            hora.pop('precipitacao', None)
        payload_antigo['de_cache'] = True
        monkeypatch.setattr(
            servicos, 'obter_previsao', lambda *_: payload_antigo)

        resposta = authenticated_client.get('/meteorologia/')
        assert resposta.status_code == 200
        assert 'Horas guardadas' in resposta.get_data(as_text=True)

    def test_com_local_e_api_em_baixo_mostra_erro(
            self, authenticated_client, monkeypatch):
        import requests
        import app.meteorologia.services as servicos

        def rebentar(*a, **k):
            raise requests.Timeout('esgotado')

        monkeypatch.setattr(servicos.requests, 'get', rebentar)
        r = authenticated_client.post('/meteorologia/api/localizacao', json={
            'nome': 'Vila Verde', 'latitude': 41.65,
            'longitude': -8.43, 'pais': 'Portugal'})
        assert r.status_code == 200
        resposta = authenticated_client.get('/meteorologia/')
        assert resposta.status_code == 200
        assert 'indisponível'.encode('utf-8') in resposta.data

    def test_campos_em_falta_mostram_traco(
            self, authenticated_client, monkeypatch):
        _mock_forecast(monkeypatch)
        r = authenticated_client.post('/meteorologia/api/localizacao', json={
            'nome': 'Vila Verde', 'latitude': 41.65,
            'longitude': -8.43, 'pais': 'Portugal'})
        assert r.status_code == 200
        resposta = authenticated_client.get('/meteorologia/')
        assert resposta.status_code == 200
        assert '—'.encode('utf-8') in resposta.data


# ── Cache da última previsão (fallback da API) ──


def _api_em_baixo(monkeypatch):
    import requests
    import app.meteorologia.services as servicos

    def rebentar(*a, **k):
        raise requests.Timeout('esgotado')

    monkeypatch.setattr(servicos.requests, 'get', rebentar)


class TestCachePrevisao:
    def test_sucesso_grava_cache_e_depois_api_em_baixo_serve_guardado(
            self, app, monkeypatch):
        from app.meteorologia import services as servicos
        _mock_forecast(monkeypatch)
        with app.app_context():
            p1 = servicos.obter_previsao(41.65, -8.43)
            assert p1 is not None
            assert not p1.get('de_cache')
        _api_em_baixo(monkeypatch)
        with app.app_context():
            p2 = servicos.obter_previsao(41.65, -8.43)
            assert p2 is not None
            assert p2['de_cache'] is True
            assert p2['atual']['temperatura'] == 21.5
            assert 'obtida_em' in p2

    def test_api_em_baixo_sem_cache_devolve_none(self, app, monkeypatch):
        from app.meteorologia import services as servicos
        _api_em_baixo(monkeypatch)
        with app.app_context():
            assert servicos.obter_previsao(41.65, -8.43) is None

    def test_cache_expirada_devolve_none(self, app, monkeypatch):
        from datetime import datetime, timedelta

        from app import db
        from app.meteorologia import services as servicos
        from app.meteorologia.models import PrevisaoCache
        _api_em_baixo(monkeypatch)
        with app.app_context():
            linha = PrevisaoCache(
                chave='41.65,-8.43',
                payload='{"atual": {"temperatura": 1.0}}',
                obtida_em=datetime.utcnow()
                - timedelta(hours=servicos.IDADE_MAXIMA_CACHE_HORAS + 1))
            db.session.add(linha)
            db.session.commit()
            assert servicos.obter_previsao(41.65, -8.43) is None

    def test_gravacao_regravada_sem_duplicados(self, app, monkeypatch):
        from app import db
        from app.meteorologia import services as servicos
        from app.meteorologia.models import PrevisaoCache
        _mock_forecast(monkeypatch)
        with app.app_context():
            servicos.obter_previsao(41.65, -8.43)
            servicos.obter_previsao(41.65, -8.43)
            assert PrevisaoCache.query.count() == 1

    def test_sem_app_context_nao_rebenta(self, monkeypatch):
        from app.meteorologia import services as servicos
        _mock_forecast(monkeypatch)
        # Sem app context: escreve/le cache e nunca levanta exceção.
        p = servicos.obter_previsao(41.65, -8.43)
        assert p is not None
        _api_em_baixo(monkeypatch)
        assert servicos.obter_previsao(41.65, -8.43) is None

    def test_index_mostra_aviso_cache(self, authenticated_client, monkeypatch):
        import app.meteorologia.services as servicos
        _mock_forecast(monkeypatch)
        r = authenticated_client.post('/meteorologia/api/localizacao', json={
            'nome': 'Vila Verde', 'latitude': 41.65,
            'longitude': -8.43, 'pais': 'Portugal'})
        assert r.status_code == 200
        # Primeira chamada preenche a cache; a segunda simula API em baixo.
        assert authenticated_client.get('/meteorologia/').status_code == 200
        _api_em_baixo(monkeypatch)
        resposta = authenticated_client.get('/meteorologia/')
        assert resposta.status_code == 200
        corpo = resposta.data.decode('utf-8')
        assert 'guardados' in corpo
        assert 'Horas guardadas' in corpo
