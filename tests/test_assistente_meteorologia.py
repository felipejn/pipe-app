"""Testes unitários da ferramenta get_meteorologia do Assistente IA.

Cobrem o registo da ferramenta, o erro quando não há localização guardada,
a previsão quando a OpenWeather responde e quando falha, o payload compacto e
detalhado (incluindo a inexistência de 'diaria' no detalhado), o tamanho do
JSON SERIALIZADO (<= 2000 chars) em compacto, detalhado e pior-caso, o
isolamento por utilizador e a frescura (meta com fonte e data).

Usam SQLite em memória (create_app('testing')), sem tocar na BD real nem na
API da OpenWeather: as chamadas HTTP são mockadas com unittest.mock.patch.
"""

from unittest import TestCase

import unittest.mock
import requests
import json

from app import create_app, db
from app.assistente.contexto import _serializar_resultado_tool
from app.assistente.ferramentas import (
    DEFINICOES_FERRAMENTAS_LEITURA,
    REGISTO_FERRAMENTAS,
    executar_ferramenta,
    get_meteorologia,
)
from app.auth.models import User


# ── Fixture de previsão realista da OpenWeather (alinhada a
#    tests/test_meteorologia.py) ────────────────────────────────────────────


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
    inicio = datetime(2026, 10, 7)
    lista = []
    codigos = [802, 804, 500, 800, 211]
    for i in range(40):
        local = inicio + timedelta(hours=3 * i)
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


class _RespostaFalsa:
    """Resposta HTTP falsa que simula o comportamento do requests.Response."""

    def __init__(self, dados):
        self._dados = dados

    def raise_for_status(self):
        return None

    def json(self):
        return self._dados


def _mock_request(url, params=None, **kwargs):
    from app.meteorologia.services import WEATHER_URL
    dados = (_tempo_atual_valido() if url == WEATHER_URL
             else _forecast_valido())
    return _RespostaFalsa(dados)


class _BaseMeteo(TestCase):
    """App isolada com SQLite em memória; as chamadas OpenWeather são mockadas."""

    def setUp(self):
        self.app = create_app('testing')
        self.app.config['OPENWEATHER_API_KEY'] = 'test-chave-testes'
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.user = User(username='meteouser', email='meteouser@pipe.local',
                         password_hash='x')
        db.session.add(self.user)
        db.session.flush()
        self.user_id = self.user.id

        self.outro_user = User(username='meteoutro',
                               email='meteoutro@pipe.local',
                               password_hash='x')
        db.session.add(self.outro_user)
        db.session.flush()
        self.outro_user_id = self.outro_user.id

        # Localizacao guardada para self.user_id (necessaria para a ferramenta).
        from app.meteorologia.models import LocalizacaoMeteorologia

        self.local = LocalizacaoMeteorologia(
            user_id=self.user_id,
            nome='Vila Verde',
            latitude=41.65,
            longitude=-8.43,
            pais='Portugal',
            regiao='Distrito de Braga',
        )
        db.session.add(self.local)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()



class RegistoFerramentaTests(_BaseMeteo):
    """A ferramenta tem de estar registada nos dois sentidos."""

    def test_registrada_no_registo_e_nas_definicoes_de_leitura(self):
        self.assertIn('get_meteorologia', REGISTO_FERRAMENTAS)
        nomes = [d['function']['name'] for d in DEFINICOES_FERRAMENTAS_LEITURA]
        self.assertIn('get_meteorologia', nomes)

    def test_definicao_expoe_parametro_detalhado(self):
        definicao = next(d for d in DEFINICOES_FERRAMENTAS_LEITURA
                         if d['function']['name'] == 'get_meteorologia')
        properties = definicao['function']['parameters']['properties']
        self.assertIn('detalhado', properties)
        self.assertEqual(properties['detalhado']['type'], 'boolean')
        self.assertIn('description', properties['detalhado'])

    def test_despachante_aceita_o_filtro(self):
        with unittest.mock.patch(
                'app.meteorologia.services.requests.get',
                side_effect=_mock_request):
            resultado = executar_ferramenta(
                'get_meteorologia', {'detalhado': True},
                self.user_id, modo='leitura')
        self.assertNotIn('erro', resultado)
        self.assertIn('horaria', resultado)


class SemLocalizacaoTests(_BaseMeteo):
    """Sem localizacao guardada, o modelo tem de ser encaminhado para o modulo."""

    def test_sem_localizacao_retorna_erro_orientador(self):
        resultado = get_meteorologia(self.outro_user_id)
        self.assertIn('erro', resultado)
        self.assertIn('Defina primeiro a localização em Meteorologia',
                      resultado['erro'])
        self.assertIn('Definir localização', resultado['erro'])



class PrevisaoTests(_BaseMeteo):
    """Previsão a partir dos payloads mockados da OpenWeather."""

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get', side_effect=_mock_request,
    )
    def test_previsao_retorna_payload_compacto_com_todos_os_campos(self, _):
        resultado = get_meteorologia(self.user_id)
        self.assertNotIn('erro', resultado)
        self.assertEqual(set(resultado), {'local', 'atual', 'diaria', 'meta'})

        local = resultado['local']
        self.assertEqual(local['nome'], 'Vila Verde')
        self.assertEqual(local['pais'], 'Portugal')
        self.assertEqual(local['regiao'], 'Distrito de Braga')
        self.assertIn('timezone', local)

        atual = resultado['atual']
        self.assertIn('temperatura', atual)
        self.assertIn('sensacao_termica', atual)
        self.assertIn('condicao', atual)
        self.assertIn('emoji', atual)
        self.assertIn('humidade', atual)
        self.assertIn('prob_precipitacao', atual)
        self.assertIn('vento', atual)
        self.assertIn('velocidade', atual['vento'])
        self.assertIn('direcao_cardinal', atual['vento'])
        self.assertIn('uv', atual)
        self.assertIn('precipitacao', atual)

        diaria = resultado['diaria']
        self.assertEqual(len(diaria), 5)
        d0 = diaria[0]
        self.assertEqual(d0['data'], '2026-10-07')
        self.assertIn('condicao', d0)
        self.assertIn('emoji', d0)
        self.assertIn('temp_max', d0)
        self.assertIn('temp_min', d0)
        self.assertIn('prob_precipitacao', d0)

        meta = resultado['meta']
        self.assertIn('atualizada_em', meta)
        self.assertIn('fonte', meta)
        self.assertEqual(meta['fonte'], 'OpenWeather')

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get', side_effect=_mock_request,
    )
    def test_payload_enxuto_sem_campos_excessivos(self, _):
        resultado = get_meteorologia(self.user_id)
        self.assertNotIn('erro', resultado)

        self.assertEqual(set(resultado), {'local', 'atual', 'diaria', 'meta'})
        self.assertEqual(set(resultado['atual']), {
            'temperatura', 'sensacao_termica', 'condicao', 'emoji',
            'humidade', 'prob_precipitacao', 'vento', 'uv', 'precipitacao'})
        self.assertEqual(set(resultado['atual']['vento']),
                         {'velocidade', 'direcao_cardinal'})
        self.assertEqual(set(resultado['diaria'][0]), {
            'data', 'condicao', 'emoji', 'temp_max', 'temp_min',
            'prob_precipitacao'})

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get',
        side_effect=requests.RequestException('timeout na API'),
    )
    def test_api_indisponivel_retorna_erro_amigavel(self, _):
        resultado = get_meteorologia(self.user_id)
        self.assertIn('erro', resultado)
        self.assertIn('indisponível', resultado['erro'].lower())
        self.assertIn('Tenta novamente mais tarde', resultado['erro'])



class DetalhadoTests(_BaseMeteo):
    """Payload detalhado: horaria reduzida e SEM diaria."""

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get', side_effect=_mock_request,
    )
    def test_payload_detalhado_inclui_horaria_reduzida(self, _):
        resultado = get_meteorologia(self.user_id, detalhado=True)
        self.assertNotIn('erro', resultado)
        self.assertIn('horaria', resultado)
        self.assertIsInstance(resultado['horaria'], list)
        # De 2 em 2 horas, das primeiras 24 -> maximo 12 itens.
        self.assertLessEqual(len(resultado['horaria']), 12)
        h0 = resultado['horaria'][0]
        self.assertIn('hora', h0)
        self.assertIn('temperatura', h0)
        self.assertIn('condicao', h0)
        self.assertIn('emoji', h0)
        self.assertIn('prob_precipitacao', h0)

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get', side_effect=_mock_request,
    )
    def test_diaria_ausente_no_detalhado(self, _):
        resultado = get_meteorologia(self.user_id, detalhado=True)
        self.assertNotIn('erro', resultado)
        self.assertNotIn('diaria', resultado)



class TamanhoTests(_BaseMeteo):
    """O JSON SERIALIZADO (como o modelo recebe) tem de caber em 2000 chars."""

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get', side_effect=_mock_request,
    )
    def test_payload_compacto_cabe_no_tecto(self, _):
        resultado = get_meteorologia(self.user_id)
        serialized = _serializar_resultado_tool(resultado)
        self.assertNotIn('erro', resultado)
        self.assertLessEqual(len(serialized), 2000)
        # O resultado nao deve trazer aviso de truncagem forçada.
        self.assertNotIn('aviso', resultado)

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get', side_effect=_mock_request,
    )
    def test_payload_detalhado_cabe_no_tecto(self, _):
        resultado = get_meteorologia(self.user_id, detalhado=True)
        serialized = _serializar_resultado_tool(resultado)
        self.assertNotIn('erro', resultado)
        self.assertLessEqual(len(serialized), 2000)
        self.assertNotIn('aviso', resultado)

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get', side_effect=_mock_request,
    )
    @unittest.mock.patch('app.meteorologia.services.descrever_wmo',
                         return_value=('Condição meteorológica extremamente longa e descritiva', '⚡'))
    def test_caso_pior_payload_longo_cabe_no_tecto(self, _1, _2):
        # Pior caso: nome de local no teto (TETO_NOME = 120) + descrições WMO
        # compridas maximizam o payload. Testa-se o JSON SERIALIZADO (como o
        # modelo recebe), em modo compacto e detalhado: <= 2000 chars, sem erro
        # nem aviso, e qualquer eventuale truncagem afecta só a lista horaria;
        # local e atual ficam sempre inteiros.
        from app.meteorologia.models import LocalizacaoMeteorologia

        local = LocalizacaoMeteorologia.query.get(self.local.id)
        local.nome = 'A' * 120
        db.session.commit()

        for detalhado in (False, True):
            resultado = get_meteorologia(self.user_id, detalhado=detalhado)
            self.assertNotIn('erro', resultado)
            serialized = _serializar_resultado_tool(resultado)
            self.assertLessEqual(len(serialized), 2000)
            self.assertNotIn('aviso', serialized)

            data = json.loads(serialized)
            # local e atual inteiros, independentemente da truncagem
            self.assertIn('local', data)
            self.assertIn('atual', data)
            self.assertEqual(data['local']['nome'], 'A' * 120)
            for chave in ('temperatura', 'sensacao_termica', 'humidade',
                          'prob_precipitacao', 'vento', 'uv', 'precipitacao'):
                self.assertIn(chave, data['atual'])
            # se houver truncagem, só afecta horaria
            if data.get('truncado'):
                self.assertEqual(data['truncado'], True)
                self.assertIn('nota', data)
                self.assertIn('horaria', data)
                self.assertLessEqual(len(data['horaria']), 10)


class IsolamentoTests(_BaseMeteo):
    """Isolamento rigoroso por utilizador."""

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get', side_effect=_mock_request,
    )
    def test_isolamento_utilizador_outro_user_sem_localizacao(self, _):
        # Outro utilizador nao tem localizacao guardada -> erro orientador.
        resultado = get_meteorologia(self.outro_user_id)
        self.assertIn('erro', resultado)
        # Este utilizador tem localizacao -> sem erro.
        resultado2 = get_meteorologia(self.user_id)
        self.assertNotIn('erro', resultado2)


class FrescuraTests(_BaseMeteo):

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get',
        side_effect=_mock_request,
    )
    def test_meta_inclui_fonte_e_data(self, _):
        resultado = get_meteorologia(self.user_id)
        self.assertNotIn('erro', resultado)
        meta = resultado['meta']
        self.assertIn('fonte', meta)
        self.assertEqual(meta['fonte'], 'OpenWeather')
        self.assertIn('atualizada_em', meta)
        # Formato ISO: AAAA-MM-DDTHH:MM
        self.assertRegex(meta['atualizada_em'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$')
