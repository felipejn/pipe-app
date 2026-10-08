"""Testes do envio automático do Resumo Diário, sempre em SQLite em memória."""
from datetime import date, datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from app import create_app, db
from app.auth.models import User
from app.modulos.models import UserModulo
from app.notifications.models import UserNotificationPreferences
from app.resumo_diario.models import ConfiguracaoResumoDiario
from app.resumo_diario import services


@pytest.fixture
def contexto():
    app = create_app('testing')
    with app.app_context():
        assert ':memory:' in app.config['SQLALCHEMY_DATABASE_URI']
        db.create_all()
        users = []
        for name in ('automatico-a', 'automatico-b'):
            user = User(username=name, email=f'{name}@example.test', password_hash='x', activo=True)
            db.session.add(user)
            db.session.flush()
            db.session.add(UserModulo(user_id=user.id, modulo_slug='resumo_diario', ativo=True))
            db.session.add(UserNotificationPreferences(
                user_id=user.id, telegram_chat_id=f'chat-{user.id}', telegram_activo=True))
            users.append(user)
        db.session.commit()
        ids = [u.id for u in users]
    yield app, ids
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _resumo(_user_id, data, opcoes=None):
    return {'data': data.isoformat(), 'secoes': {}, 'texto': 'Resumo de teste'}


def test_elegibilidade_cada_condicao_falhada_isoladamente(contexto):
    app, (user_id, _) = contexto
    with app.app_context():
        user = db.session.get(User, user_id)
        assert services.utilizador_elegivel_para_resumo(user)
        user_modulo = UserModulo.query.filter_by(
            user_id=user_id, modulo_slug='resumo_diario').one()
        user_modulo.ativo = False
        assert not services.utilizador_elegivel_para_resumo(user)
        user_modulo.ativo = True
        user.notificacao_prefs.telegram_chat_id = None
        assert not services.utilizador_elegivel_para_resumo(user)
        user.notificacao_prefs.telegram_chat_id = '   '
        assert not services.utilizador_elegivel_para_resumo(user)
        user.notificacao_prefs.telegram_chat_id = 'chat'
        user.notificacao_prefs.telegram_activo = False
        assert not services.utilizador_elegivel_para_resumo(user)


def test_envio_regista_data_e_nao_repete_no_mesmo_dia(contexto):
    app, ids = contexto
    user_id = ids[0]
    hoje = date(2026, 10, 9)
    with app.app_context(), patch.object(services, 'gerar_resumo_diario', side_effect=_resumo), \
            patch.object(services.notification_service, 'send', return_value={'telegram': True}) as enviar:
        assert services.enviar_resumos_diarios(hoje) == set(ids)
        config = ConfiguracaoResumoDiario.query.filter_by(user_id=user_id).one()
        assert config.ultimo_envio == hoje
        services.enviar_resumos_diarios(hoje)
        assert enviar.call_count == 2


def test_falha_nao_regista_e_isolamento_por_utilizador(contexto):
    app, (user_a, user_b) = contexto
    hoje = date(2026, 10, 9)
    with app.app_context(), patch.object(services, 'gerar_resumo_diario', side_effect=_resumo), \
            patch.object(services.notification_service, 'send',
                         side_effect=[RuntimeError('erro no Telegram'), {'telegram': True}]):
        assert services.enviar_resumos_diarios(hoje) == {user_b}
        assert ConfiguracaoResumoDiario.query.filter_by(user_id=user_a).first() is None
        assert ConfiguracaoResumoDiario.query.filter_by(user_id=user_b).one().ultimo_envio == hoje


def test_token_ausente_nao_regista_e_tenta_os_restantes(contexto):
    app, ids = contexto
    hoje = date(2026, 10, 9)
    with app.app_context(), patch.object(services, 'gerar_resumo_diario', side_effect=_resumo), \
            patch.object(services.notification_service, 'send',
                         return_value={'telegram': None}) as enviar:
        assert services.enviar_resumos_diarios(hoje) == set()
        assert enviar.call_count == len(ids)
        assert ConfiguracaoResumoDiario.query.count() == 0


def test_chat_id_ausente_e_ignorado_sem_impedir_outro_utilizador(contexto):
    app, (user_a, user_b) = contexto
    hoje = date(2026, 10, 9)
    with app.app_context():
        db.session.get(User, user_a).notificacao_prefs.telegram_chat_id = None
        db.session.commit()
        with patch.object(services, 'gerar_resumo_diario', side_effect=_resumo), \
                patch.object(services.notification_service, 'send',
                             return_value={'telegram': True}) as enviar:
            assert services.enviar_resumos_diarios(hoje) == {user_b}
            assert enviar.call_count == 1


def test_simulacao_nao_envia_nem_grava(contexto):
    app, (user_id, _) = contexto
    with app.app_context(), patch.object(services, 'gerar_resumo_diario', side_effect=_resumo), \
            patch.object(services.notification_service, 'send') as enviar:
        assert services.enviar_resumos_diarios(date(2026, 10, 9), simular=True) == set()
        enviar.assert_not_called()
        assert ConfiguracaoResumoDiario.query.filter_by(user_id=user_id).first() is None


def test_data_local_perto_da_meia_noite_utc():
    instante = datetime(2026, 10, 8, 23, 30, tzinfo=timezone.utc)
    class Relogio:
        @staticmethod
        def now(fuso):
            return instante.astimezone(fuso)
    with patch.object(services, 'datetime', Relogio):
        assert services.obter_data_local() == date(2026, 10, 9)


def test_reexecucao_da_task_omite_utilizadores_que_ja_receberam(contexto):
    from scripts import pipe_tasks
    app, ids = contexto
    ordem = []
    def chamada(nome, resultado=None):
        def executar(*args):
            ordem.append(nome)
            if isinstance(resultado, Exception):
                raise resultado
            return resultado
        return executar
    with app.app_context(), \
            patch.object(pipe_tasks, 'tarefa_euromilhoes', side_effect=chamada('euro')), \
            patch.object(pipe_tasks, 'tarefa_combustiveis', side_effect=chamada('combustiveis', RuntimeError('falha simulada'))), \
            patch.object(services, 'enviar_resumos_diarios', side_effect=chamada('resumo', set(ids))), \
            patch.object(pipe_tasks, 'tarefa_tarefas', side_effect=chamada('tarefas')), \
            patch.object(pipe_tasks, 'tarefa_calendario', side_effect=chamada('calendario')):
        pipe_tasks.executar_tarefas_diarias(date(2026, 10, 9))
    assert ordem == ['euro', 'combustiveis', 'resumo', 'tarefas', 'calendario']
