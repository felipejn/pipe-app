"""Testes do Resumo Diário sem rede e com SQLite em memória."""

from datetime import date, datetime
from unittest.mock import patch

import pytest

from app import create_app, db
from app.auth.models import User
from app.calendario.models import Evento
from app.combustiveis.models import (
    EstadoAtualizacaoCombustiveis,
    Posto,
    PrecoHistorico,
    UtilizadorCombustivel,
    UtilizadorConcelho,
)
from app.meteorologia.models import LocalizacaoMeteorologia
from app.resumo_diario.services import gerar_resumo_diario, obter_data_local
from app.tarefas.models import Lista, Tarefa


@pytest.fixture
def contexto():
    app = create_app('testing')
    with app.app_context():
        assert ':memory:' in app.config['SQLALCHEMY_DATABASE_URI']
        db.create_all()
        utilizador = User(username='resumo', email='resumo@example.test', password_hash='x')
        outro = User(username='outro-resumo', email='outro-resumo@example.test', password_hash='x')
        db.session.add_all([utilizador, outro])
        db.session.flush()
        lista = Lista(nome='Geral', user_id=utilizador.id)
        outra_lista = Lista(nome='Geral', user_id=outro.id)
        db.session.add_all([lista, outra_lista])
        db.session.commit()
        yield utilizador.id, outro.id, lista.id, outra_lista.id
        db.session.remove()
        db.drop_all()


def _previsao(datas):
    return {
        'diaria': [
            {'data': dia.isoformat(), 'temp_min': 12.4, 'temp_max': 23.6,
             'prob_precipitacao': 35, 'descricao_pt': 'Chuva fraca'}
            for dia in datas
        ]
    }


def _evento(user_id, titulo, inicio, fim=None, notificar=False):
    db.session.add(Evento(
        user_id=user_id, titulo=titulo, data_inicio=inicio,
        data_fim=fim or inicio.replace(hour=inicio.hour + 1),
        notificar=notificar,
    ))


def _tarefa(user_id, lista_id, texto, prazo, concluida=False):
    db.session.add(Tarefa(
        user_id=user_id, lista_id=lista_id, texto=texto,
        data_limite=prazo, concluida=concluida,
    ))


def test_dia_normal_inclui_eventos_tarefas_e_omite_amanha_vazia(contexto):
    user_id, _, lista_id, _ = contexto
    hoje = date(2026, 10, 7)  # quarta-feira
    _evento(user_id, 'Evento de hoje', datetime(2026, 10, 7, 9), notificar=False)
    _evento(user_id, 'Evento de amanhã', datetime(2026, 10, 8, 15))
    _tarefa(user_id, lista_id, 'Entregar relatório', hoje)
    _tarefa(user_id, lista_id, 'Tarefa atrasada', date(2026, 10, 5))
    _tarefa(user_id, lista_id, 'Concluída', date(2026, 10, 6), concluida=True)
    db.session.commit()

    with patch('app.resumo_diario.services.meteorologia_services.obter_previsao',
               return_value=_previsao([hoje, date(2026, 10, 8)])):
        resultado = gerar_resumo_diario(user_id, hoje)

    assert resultado['secoes']['meteorologia']['temp_min'] == 12.4
    assert resultado['secoes']['eventos_hoje'][0]['titulo'] == 'Evento de hoje'
    assert resultado['secoes']['tarefas_hoje'][0]['titulo'] == 'Entregar relatório'
    assert resultado['secoes']['tarefas_atrasadas'][0]['titulo'] == 'Tarefa atrasada'
    assert resultado['secoes']['eventos_amanha'][0]['titulo'] == 'Evento de amanhã'
    assert 'Evento de hoje' in resultado['texto']
    assert 'Amanhã' in resultado['texto']


def test_isolamento_entre_utilizadores(contexto):
    user_id, outro_id, lista_id, outra_lista_id = contexto
    hoje = date(2026, 10, 7)
    _evento(user_id, 'Privado A', datetime(2026, 10, 7, 10))
    _evento(outro_id, 'Privado B', datetime(2026, 10, 7, 11))
    _tarefa(user_id, lista_id, 'Tarefa A', hoje)
    _tarefa(outro_id, outra_lista_id, 'Tarefa B', hoje)
    db.session.add_all([
        LocalizacaoMeteorologia(user_id=user_id, nome='Braga', latitude=41.55,
                                longitude=-8.42, pais='Portugal'),
        LocalizacaoMeteorologia(user_id=outro_id, nome='Porto', latitude=41.15,
                                longitude=-8.61, pais='Portugal'),
    ])
    db.session.commit()
    chamadas = []

    def previsao(lat, lon):
        chamadas.append((lat, lon))
        return _previsao([hoje])

    with patch('app.resumo_diario.services.meteorologia_services.obter_previsao',
               side_effect=previsao):
        resultado = gerar_resumo_diario(user_id, hoje)

    assert [e['titulo'] for e in resultado['secoes']['eventos_hoje']] == ['Privado A']
    assert [t['titulo'] for t in resultado['secoes']['tarefas_hoje']] == ['Tarefa A']
    assert chamadas == [(41.55, -8.42)]


def test_meteorologia_indisponivel_e_secções_vazias_sao_omitidas(contexto):
    user_id, _, _, _ = contexto
    with patch('app.resumo_diario.services.meteorologia_services.obter_previsao',
               return_value=None):
        resultado = gerar_resumo_diario(user_id, date(2026, 10, 7))
    assert resultado['secoes'] == {}
    assert resultado['texto'] == ''


def test_terca_inclui_mais_barato_estado_e_preco_com_tres_decimais(contexto):
    user_id, outro_id, _, _ = contexto
    dia = date(2026, 10, 6)  # terça-feira
    posto = Posto(id=801, nome='Posto Braga', concelho='Braga', ativo=True)
    db.session.add(posto)
    db.session.flush()
    db.session.add_all([
        PrecoHistorico(posto_id=posto.id, tipo_combustivel='Gasóleo simples',
                       preco=1.7894, data_atualizacao_dgeg='2030-01-01T00:00:00Z',
                       data_recolha=datetime(2026, 10, 6, 6)),
        UtilizadorConcelho(user_id=user_id, concelho='Braga'),
        UtilizadorCombustivel(user_id=user_id, tipo_combustivel='Gasóleo simples'),
        UtilizadorConcelho(user_id=outro_id, concelho='Porto'),
        UtilizadorCombustivel(user_id=outro_id, tipo_combustivel='Gasolina 95'),
    ])
    estado = EstadoAtualizacaoCombustiveis.query.filter_by(id=1).first()
    estado.ultima_atualizacao = datetime(2026, 10, 6, 6)
    estado.ultima_execucao_sucesso = False
    estado.mensagem_erro = 'timeout'
    db.session.commit()

    with patch('app.resumo_diario.services.meteorologia_services.obter_previsao',
               return_value=None):
        resultado = gerar_resumo_diario(user_id, dia)
    combustiveis = resultado['secoes']['combustiveis']
    assert combustiveis['mais_barato_por_tipo'][0]['preco'] == 1.789
    assert combustiveis['recolha']['sucesso'] is False
    assert '1,789 €/L' in resultado['texto']
    assert 'timeout' in resultado['texto']
    assert 'Porto' not in resultado['texto']


def test_sexta_inclui_previsao_e_eventos_de_sabado_e_domingo(contexto):
    user_id, _, _, _ = contexto
    sexta = date(2026, 10, 9)
    sabado, domingo = date(2026, 10, 10), date(2026, 10, 11)
    _evento(user_id, 'Almoço de sábado', datetime(2026, 10, 10, 12))
    _evento(user_id, 'Passeio de domingo', datetime(2026, 10, 11, 10))
    db.session.commit()
    with patch('app.resumo_diario.services.meteorologia_services.obter_previsao',
               return_value=_previsao([sexta, sabado, domingo])):
        resultado = gerar_resumo_diario(user_id, sexta)
    fim_de_semana = resultado['secoes']['fim_de_semana']
    assert fim_de_semana['sabado']['eventos'][0]['titulo'] == 'Almoço de sábado'
    assert fim_de_semana['domingo']['eventos'][0]['titulo'] == 'Passeio de domingo'
    assert fim_de_semana['sabado']['meteorologia']['temp_max'] == 23.6
    assert 'Almoço de sábado' in resultado['texto']


def test_limite_remove_secção_inteira_sem_cortar_linhas(contexto):
    user_id, _, _, _ = contexto
    sexta = date(2026, 10, 9)
    _evento(user_id, 'X' * 1000, datetime(2026, 10, 11, 10))
    db.session.commit()
    with patch('app.resumo_diario.services.meteorologia_services.obter_previsao',
               return_value=_previsao([sexta, date(2026, 10, 10), date(2026, 10, 11)])):
        resultado = gerar_resumo_diario(user_id, sexta)
    assert len(resultado['texto']) <= 900
    assert 'X' * 1000 not in resultado['texto']
    assert resultado['texto'].startswith('Meteorologia:')


def test_localizacao_padrao_e_data_local(contexto):
    user_id, _, _, _ = contexto
    with patch('app.resumo_diario.services.meteorologia_services.obter_previsao',
               return_value=_previsao([date(2026, 10, 7)])) as previsao:
        gerar_resumo_diario(user_id, date(2026, 10, 7))
    previsao.assert_called_once_with(41.545448, -8.426507)
    from app.resumo_diario.services import FUSO_HORARIO
    assert FUSO_HORARIO.key == 'Europe/Lisbon'
    assert isinstance(obter_data_local(), date)


def test_open_meteo_usa_weather_code_documentado_e_mantem_formato_normalizado():
    from app.meteorologia import services as meteorologia

    class Resposta:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                'timezone': 'Europe/Lisbon',
                'current': {'time': '2026-10-07T12:00', 'temperature_2m': 20,
                            'weather_code': 2},
                'hourly': {'time': [], 'weather_code': [],
                           'temperature_2m': [], 'precipitation_probability': []},
                'daily': {'time': ['2026-10-07'], 'weather_code': [61],
                          'temperature_2m_max': [22], 'temperature_2m_min': [13],
                          'precipitation_probability_max': [45]},
            }

    with patch.object(meteorologia.requests, 'get', return_value=Resposta()) as pedido:
        previsao = meteorologia.obter_previsao(41.55, -8.42)
    assert 'weather_code' in pedido.call_args.kwargs['params']['daily']
    assert previsao['diaria'][0]['codigo_wmo'] == 61
    assert previsao['diaria'][0]['temp_min'] == 13
