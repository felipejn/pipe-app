"""Testes de resiliência da recolha do módulo Combustíveis."""

from unittest.mock import Mock

import pytest
import requests

from app import create_app, db
from app.combustiveis import services
from app.combustiveis.models import EstadoAtualizacaoCombustiveis


class _Resposta:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code = status
        self.payload = payload
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'HTTP {self.status_code}')

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


@pytest.fixture
def contexto_combustiveis():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        if EstadoAtualizacaoCombustiveis.query.get(1) is None:
            db.session.add(EstadoAtualizacaoCombustiveis(id=1))
            db.session.commit()
        yield
        db.session.remove()
        db.drop_all()


def test_get_repete_erros_de_conexao_e_timeout(monkeypatch):
    monkeypatch.setattr(services.time, 'sleep', lambda _segundos: None)
    session = Mock()
    session.get.side_effect = [
        requests.ConnectionError('sem ligação'),
        requests.Timeout('tempo excedido'),
        _Resposta(payload={'data': []}),
    ]

    resposta = services._get_com_retry(session, {'fuel': 'diesel'})

    assert resposta.status_code == 200
    assert session.get.call_count == 3


def test_get_repete_503_ate_ao_limite(monkeypatch):
    monkeypatch.setattr(services.time, 'sleep', lambda _segundos: None)
    session = Mock()
    session.get.return_value = _Resposta(status=503)

    with pytest.raises(requests.HTTPError, match='HTTP 503'):
        services._get_com_retry(session, {'fuel': 'diesel'})

    assert session.get.call_count == services.TENTATIVAS_MAX


def test_json_invalido_repete_a_mesma_pagina(monkeypatch):
    monkeypatch.setattr(services.time, 'sleep', lambda _segundos: None)
    session = Mock()
    session.get.side_effect = [
        _Resposta(payload=ValueError('HTML em vez de JSON')),
        _Resposta(payload=ValueError('corpo vazio')),
        _Resposta(payload={'data': []}),
    ]

    payload = services._json_com_retry(session, {'fuel': 'diesel', 'page': 1})

    assert payload == {'data': []}
    assert session.get.call_count == 3


def test_json_invalido_esgota_tentativas_com_mensagem_clara(monkeypatch):
    monkeypatch.setattr(services.time, 'sleep', lambda _segundos: None)
    session = Mock()
    session.get.return_value = _Resposta(payload=ValueError('HTML'))

    with pytest.raises(requests.RequestException, match='JSON inválida'):
        services._json_com_retry(session, {'fuel': 'diesel', 'page': 1})

    assert session.get.call_count == services.TENTATIVAS_MAX


def test_falha_de_rede_num_combustivel_nao_interrompe_o_seguinte(
        contexto_combustiveis, monkeypatch):
    monkeypatch.setattr(services, 'FUEL_SLUGS', ['diesel', 'diesel_plus'])
    paginar = Mock(side_effect=[requests.ConnectionError('API indisponível'), []])
    monkeypatch.setattr(services, '_paginar_fuel', paginar)

    resultado = services.atualizar_precos_se_necessario(forcar=True)

    assert paginar.call_count == 2
    assert resultado['sucesso'] is False
    assert 'Falhou fuel=diesel' in resultado['erro']
    assert 'API indisponível' in resultado['erro']
    estado = EstadoAtualizacaoCombustiveis.query.get(1)
    assert estado.ultima_execucao_sucesso is False


def test_erro_de_processamento_isola_o_combustivel_seguinte(
        contexto_combustiveis, monkeypatch):
    monkeypatch.setattr(services, 'FUEL_SLUGS', ['diesel', 'diesel_plus'])
    paginar = Mock(side_effect=[[{'name': 'Posto sem identificador'}], []])
    monkeypatch.setattr(services, '_paginar_fuel', paginar)

    resultado = services.atualizar_precos_se_necessario(forcar=True)

    assert paginar.call_count == 2
    assert resultado['sucesso'] is False
    assert 'erro ao processar os dados (KeyError' in resultado['erro']


def test_estrutura_json_invalida_nao_interrompe_os_outros_combustiveis(
        contexto_combustiveis, monkeypatch):
    monkeypatch.setattr(services, 'FUEL_SLUGS', ['diesel', 'diesel_plus'])
    paginar = Mock(side_effect=[AttributeError("'list' object has no attribute 'get'"), []])
    monkeypatch.setattr(services, '_paginar_fuel', paginar)

    resultado = services.atualizar_precos_se_necessario(forcar=True)

    assert paginar.call_count == 2
    assert resultado['sucesso'] is False
    assert 'erro ao processar os dados (AttributeError' in resultado['erro']


def test_falha_no_commit_fica_registada_no_estado(contexto_combustiveis, monkeypatch):
    monkeypatch.setattr(services, 'FUEL_SLUGS', [])
    sessao = db.session()
    commit_original = sessao.commit
    chamadas = {'total': 0}

    def commit_com_falha_na_primeira_tentativa():
        chamadas['total'] += 1
        if chamadas['total'] == 1:
            raise RuntimeError('disco indisponível')
        return commit_original()

    monkeypatch.setattr(sessao, 'commit', commit_com_falha_na_primeira_tentativa)

    resultado = services.atualizar_precos_se_necessario(forcar=True)

    assert resultado['sucesso'] is False
    assert resultado['postos_verificados'] == 0
    assert resultado['precos_novos'] == 0
    assert 'Falha ao guardar a recolha na base de dados' in resultado['erro']
    estado = EstadoAtualizacaoCombustiveis.query.get(1)
    assert estado.ultima_execucao_sucesso is False
    assert 'disco indisponível' in estado.mensagem_erro
