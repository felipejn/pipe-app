"""Testes unitários da ferramenta get_meteorologia do Assistente IA.

Cobrem o registo da ferramenta, o erro quando não há localização guardada,
a previsão quando a Open-Meteo responde e quando falha, o payload compacto e
detalhado (incluindo a inexistência de 'diaria' no detalhado), o tamanho do
JSON SERIALIZADO (<= 2000 chars) em compacto, detalhado e pior-caso, o
isolamento por utilizador e a frescura (meta com fonte e data).

Usam SQLite em memória (create_app('testing')), sem tocar na BD real nem na
API da Open-Meteo: a chamada HTTP é mockada com unittest.mock.patch.
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


# ── Fixture de previsao realista da Open-Meteo (alinhado a
#    tests/test_meteorologia.py) ────────────────────────────────────────────


def _horas_7dias():
    from datetime import datetime as _dt, timedelta as _td

    base = _dt(2026, 10, 7, 0, 0)
    return [(base + _td(hours=i)).strftime('%Y-%m-%dT%H:00') for i in range(168)]


def _forecast_valido():
    horas = _horas_7dias()
    probs = [5] * 168
    probs[14] = 42
    return {
        'latitude': 41.65,
        'longitude': -8.43,
        'timezone': 'Europe/Lisbon',
        'current': {
            'time': '2026-10-07T14:00',
            'temperature_2m': 21.5,
            'relative_humidity_2m': 60,
            'apparent_temperature': 22.3,
            'precipitation': 0.0,
            'weathercode': 2,
            'wind_speed_10m': 12.5,
            'wind_direction_10m': 90,
            'uv_index': 3.5,
        },
        'hourly': {
            'time': horas,
            'temperature_2m': [10.0 + i * 0.1 for i in range(168)],
            'weathercode': [2] * 168,
            'precipitation_probability': probs,
        },
        'daily': {
            'time': ['2026-10-07', '2026-10-08', '2026-10-09',
                     '2026-10-10', '2026-10-11', '2026-10-12', '2026-10-13'],
            'weathercode': [2, 3, 61, 0, 1, 80, 95],
            'temperature_2m_max': [24.0, 23.5, 22.0, 21.0, 20.5,
                                   19.0, 18.5],
            'temperature_2m_min': [14.0, 13.5, 13.0, 12.5, 12.0,
                                   11.5, 11.0],
            'precipitation_probability_max': [10, 20, 30, 0, 5, 60, 80],
        },
    }


class _RespostaFalsa:
    """Resposta HTTP falsa que simula o comportamento do requests.Response."""

    def __init__(self, dados):
        self._dados = dados

    def raise_for_status(self):
        return None

    def json(self):
        return self._dados


class _BaseMeteo(TestCase):
    """App isolada com SQLite em memória; a HTTP para Open-Meteo é mockada."""

    def setUp(self):
        self.app = create_app('testing')
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
        resultado = executar_ferramenta('get_meteorologia', {'detalhado': True},
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
    """Previsao a partir do payload mockado da Open-Meteo."""

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get',
        return_value=_RespostaFalsa(_forecast_valido()),
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
        self.assertEqual(len(diaria), 7)
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
        self.assertEqual(meta['fonte'], 'Open-Meteo')

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get',
        return_value=_RespostaFalsa(_forecast_valido()),
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
        'app.meteorologia.services.requests.get',
        return_value=_RespostaFalsa(_forecast_valido()),
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
        'app.meteorologia.services.requests.get',
        return_value=_RespostaFalsa(_forecast_valido()),
    )
    def test_diaria_ausente_no_detalhado(self, _):
        resultado = get_meteorologia(self.user_id, detalhado=True)
        self.assertNotIn('erro', resultado)
        self.assertNotIn('diaria', resultado)



class TamanhoTests(_BaseMeteo):
    """O JSON SERIALIZADO (como o modelo recebe) tem de caber em 2000 chars."""

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get',
        return_value=_RespostaFalsa(_forecast_valido()),
    )
    def test_payload_compacto_cabe_no_tecto(self, _):
        resultado = get_meteorologia(self.user_id)
        serialized = _serializar_resultado_tool(resultado)
        self.assertNotIn('erro', resultado)
        self.assertLessEqual(len(serialized), 2000)
        # O resultado nao deve trazer aviso de truncagem forçada.
        self.assertNotIn('aviso', resultado)

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get',
        return_value=_RespostaFalsa(_forecast_valido()),
    )
    def test_payload_detalhado_cabe_no_tecto(self, _):
        resultado = get_meteorologia(self.user_id, detalhado=True)
        serialized = _serializar_resultado_tool(resultado)
        self.assertNotIn('erro', resultado)
        self.assertLessEqual(len(serialized), 2000)
        self.assertNotIn('aviso', resultado)

    @unittest.mock.patch(
        'app.meteorologia.services.requests.get',
        return_value=_RespostaFalsa(_forecast_valido()),
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
        'app.meteorologia.services.requests.get',
        return_value=_RespostaFalsa(_forecast_valido()),
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
        return_value=_RespostaFalsa(_forecast_valido()),
    )
    def test_meta_inclui_fonte_e_data(self, _):
        resultado = get_meteorologia(self.user_id)
        self.assertNotIn('erro', resultado)
        meta = resultado['meta']
        self.assertIn('fonte', meta)
        self.assertEqual(meta['fonte'], 'Open-Meteo')
        self.assertIn('atualizada_em', meta)
        # Formato ISO: AAAA-MM-DDTHH:MM
        self.assertRegex(meta['atualizada_em'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$')
