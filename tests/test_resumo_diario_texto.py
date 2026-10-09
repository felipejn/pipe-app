"""Ajustes de texto do Resumo Diário (rótulos, precipitação, formato PT-PT).

NÃO é a fase 4 (LLM) — são os retoques de apresentação do texto
determinístico antes dela:

1. Duas execuções seguidas no mesmo dia: a segunda não reenvia.
2. Task completa com Telegram desligado: sem resumo, avisos antigos continuam.
3. Rótulos "Vencem hoje"/"Em atraso" no bloco de tarefas.
4. "precipitação 0%" é omitida da linha de meteorologia.
5. Preços com vírgula decimal (1,789 €/L) e data da recolha em dd/mm/aaaa hh:mm.

Tudo em SQLite em memória, sem rede.
"""
from datetime import date, datetime
from unittest.mock import patch

import pytest

from app import create_app, db
from app.auth.models import User
from app.calendario.models import Evento
from app.modulos.models import UserModulo
from app.notifications.models import UserNotificationPreferences
from app.resumo_diario import services
from app.resumo_diario.models import ConfiguracaoResumoDiario
from app.tarefas.models import Lista, Tarefa


@pytest.fixture
def contexto():
    app = create_app('testing')
    with app.app_context():
        assert ':memory:' in app.config['SQLALCHEMY_DATABASE_URI']
        db.create_all()
        user = User(username='fecho-a', email='fecho-a@example.test',
                    password_hash='x', activo=True)
        db.session.add(user)
        db.session.flush()
        db.session.add(UserModulo(user_id=user.id, modulo_slug='resumo_diario',
                                 ativo=True))
        db.session.add(UserNotificationPreferences(
            user_id=user.id, telegram_chat_id='chat-fecho',
            telegram_activo=True))
        lista = Lista(nome='Geral', user_id=user.id)
        db.session.add(lista)
        db.session.commit()
        yield app, user.id, lista.id
        db.session.remove()
        db.drop_all()


def _resumo_fixo(_user_id, data, opcoes=None):
    return {'data': data.isoformat(), 'secoes': {}, 'texto': 'Resumo de teste'}


def test_segunda_execucao_no_mesmo_dia_nao_reenvia(contexto):
    app, _, _ = contexto
    hoje = date(2026, 10, 9)
    with app.app_context(), \
            patch.object(services, 'gerar_resumo_diario', side_effect=_resumo_fixo), \
            patch.object(services.notification_service, 'send',
                         return_value={'telegram': True}) as enviar:
        primeira = services.enviar_resumos_diarios(hoje)
        segunda = services.enviar_resumos_diarios(hoje)
    assert len(primeira) == 1
    assert segunda == primeira
    assert enviar.call_count == 1


def test_telegram_desligado_sem_resumo_e_avisos_antigos_continuam(contexto):
    """Telegram desligado: nada de resumo, e a task completa mantém os
    avisos antigos de tarefas/calendário (recebidos vazio)."""
    from scripts import pipe_tasks

    app, user_id, lista_id = contexto
    hoje = date(2026, 10, 9)
    with app.app_context():
        db.session.get(User, user_id).notificacao_prefs.telegram_activo = False
        db.session.add(Tarefa(texto='Vence hoje', concluida=False,
                              data_limite=hoje, lista_id=lista_id,
                              user_id=user_id))
        db.session.add(Evento(
            user_id=user_id, titulo='Reunião amanhã',
            data_inicio=datetime(2026, 10, 10, 10),
            data_fim=datetime(2026, 10, 10, 11), notificar=True))
        db.session.commit()
        with patch.object(services.notification_service, 'send',
                          return_value={'telegram': True}) as enviar_resumo, \
                patch('app.notifications.notification_service') as enviar_antigos:
            recebidos = pipe_tasks.executar_tarefas_diarias(hoje)
    assert recebidos == set()
    enviar_resumo.assert_not_called()
    # Os avisos antigos continuam: 1 chamada de tarefas + 1 de calendário.
    assert enviar_antigos.send.call_count == 2


def test_task_completa_resumo_chega_sozinho_sem_aviso_antigo(contexto):
    """Task completa com Telegram ligado: chega só o resumo; os avisos
    antigos de tarefas/calendário são suprimidos nesse dia."""
    from scripts import pipe_tasks

    app, user_id, lista_id = contexto
    hoje = date(2026, 10, 9)
    with app.app_context():
        db.session.add(Tarefa(texto='Vence hoje', concluida=False,
                              data_limite=hoje, lista_id=lista_id,
                              user_id=user_id))
        db.session.commit()
        with patch.object(services, 'gerar_resumo_diario',
                          side_effect=_resumo_fixo), \
                patch.object(services.notification_service, 'send',
                             return_value={'telegram': True}), \
                patch('app.notifications.notification_service') as enviar_antigos:
            recebidos = pipe_tasks.executar_tarefas_diarias(hoje)
    assert recebidos == {user_id}
    enviar_antigos.send.assert_not_called()


def test_rotulos_vencem_hoje_e_em_atraso():
    bloco = services._renderizar_tarefas(
        [{'titulo': 'Relatório', 'prioridade': 2, 'prazo': '2026-10-09'}],
        [{'titulo': 'Factura', 'prioridade': 1, 'prazo': '2026-10-07'}])
    assert 'Vencem hoje: Relatório' in bloco
    assert 'Em atraso (2026-10-07): Factura' in bloco
    assert '\nHoje:' not in bloco


@pytest.mark.parametrize('prob,esperado', [
    (0, False),
    (0.4, False),  # arredonda para 0 → omitida
    (35, True),
])
def test_precipitacao_zero_e_omitida(prob, esperado):
    linha = services._linha_meteorologia({
        'temp_min': 11, 'temp_max': 23,
        'probabilidade_precipitacao': prob, 'descricao': 'Encoberto'})
    assert ('precipitação' in linha) is esperado
    assert linha.startswith('11–23 °C')
    assert linha.endswith('Encoberto')


def test_precipitacao_em_falta_nao_rebenta():
    linha = services._linha_meteorologia({
        'temp_min': 11, 'temp_max': 23, 'descricao': 'Limpo'})
    assert linha == '11–23 °C, Limpo'


def test_preco_com_virgula_e_recolha_em_formato_pt():
    bloco = services._renderizar_combustiveis({
        'mais_barato_por_tipo': [{
            'tipo_combustivel': 'Gasóleo simples', 'preco': 1.789,
            'posto': 'Posto Braga', 'concelho': 'Braga'}],
        'recolha': {'ultima_atualizacao': '2026-10-06 06:00',
                    'sucesso': True, 'erro': None}})
    assert 'Gasóleo simples: 1,789 €/L — Posto Braga (Braga)' in bloco
    assert 'Última recolha: 06/10/2026 06:00' in bloco
    assert '1.789' not in bloco
    assert '2026-10-06' not in bloco


def test_recolha_sem_data_mostra_desconhecida():
    bloco = services._renderizar_combustiveis({
        'mais_barato_por_tipo': [{
            'tipo_combustivel': 'Gasóleo simples', 'preco': 2,
            'posto': 'Posto', 'concelho': 'Braga'}],
        'recolha': {'ultima_atualizacao': None, 'sucesso': True, 'erro': None}})
    assert 'Última recolha: data desconhecida' in bloco
    assert '2,000 €/L' in bloco
