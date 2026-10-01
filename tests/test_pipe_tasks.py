"""Notificações diárias do pipe_tasks: tarefas e calendário.

Tarefas: avisam no dia do prazo («Vencem hoje») e depois em todos os dias de
atraso até concluir, 1× por dia (dedupe por `notificada_em`).
Calendário: avisam no dia anterior («Amanhã») e no dia («Hoje»); o campo único
`Evento.notificado_em` cobre os dois avisos sem migração de BD.

Spec: docs/superpowers/specs/2026-10-01-notificacoes-tarefas-calendario-design.md
"""
import os
import sys
from datetime import date, datetime, timedelta
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))

from app import create_app, db
from app.auth.models import User
from app.calendario.models import Evento
from app.tarefas.models import Lista, Tarefa

import pipe_tasks


@pytest.fixture
def app():
    """App de teste com SQLite in-memory (nunca toca em instance/pipe.db)."""
    app = create_app('testing')
    with app.app_context():
        uri = str(db.engine.url)
        assert 'memory' in uri, f'ABORTADO: os testes apontam para a BD real ({uri}).'
        db.create_all()
        yield app
        db.session.remove()


@pytest.fixture
def enviar():
    """Captura as chamadas a notification_service.send (nada é enviado a sério)."""
    with mock.patch('app.notifications.notification_service.send') as m:
        yield m


def _criar_user(username):
    user = User(username=username, email=f'{username}@exemplo.pt')
    user.set_password('password-de-teste-123')
    user.activo = True
    db.session.add(user)
    db.session.flush()
    lista = Lista(nome='Geral', user_id=user.id)
    db.session.add(lista)
    db.session.flush()
    return user, lista


def _criar_tarefa(lista, user, texto, data_limite, concluida=False, notificada_em=None):
    t = Tarefa(texto=texto, concluida=concluida, data_limite=data_limite,
               notificada_em=notificada_em, lista_id=lista.id, user_id=user.id)
    db.session.add(t)
    db.session.commit()
    return t


def _criar_evento(user, data_inicio, horas=1, dia_inteiro=False, notificar=True,
                  titulo='Evento', notificado_em=None, localizacao=None):
    e = Evento(user_id=user.id, titulo=titulo, localizacao=localizacao,
               data_inicio=data_inicio, data_fim=data_inicio + timedelta(hours=horas),
               dia_inteiro=dia_inteiro, notificar=notificar,
               notificado_em=notificado_em, cor='tomate')
    db.session.add(e)
    db.session.commit()
    return e


def _chamadas(enviar):
    """Dict {username: kwargs} das chamadas a send()."""
    return {c.kwargs['user'].username: c.kwargs for c in enviar.call_args_list}


def test_import_do_script_nao_cria_app():
    """Importar pipe_tasks não pode criar a app (BD real) — pré-requisito dos testes."""
    assert not hasattr(pipe_tasks, 'app'), (
        'pipe_tasks tem `app` no âmbulo de módulo — mover create_app() para __main__.')


def test_tarefas_avisa_no_dia_do_prazo(app, enviar):
    hoje = date.today()
    user, lista = _criar_user('util-tarefas')
    t = _criar_tarefa(lista, user, 'Pagar factura', hoje)

    pipe_tasks.tarefa_tarefas(hoje)

    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert kw['type'] == 'tarefa_lembrete'
    assert 'hoje' in kw['subject'].lower()
    assert 'atraso' not in kw['subject'].lower()
    assert 'Pagar factura' in kw['body']
    db.session.refresh(t)
    assert t.notificada_em == hoje


def test_tarefas_nao_repete_no_mesmo_dia(app, enviar):
    hoje = date.today()
    user, lista = _criar_user('util-dedupe')
    _criar_tarefa(lista, user, 'Tarefa única', hoje)

    pipe_tasks.tarefa_tarefas(hoje)
    pipe_tasks.tarefa_tarefas(hoje)   # segunda corrida no mesmo dia

    assert enviar.call_count == 1


def test_tarefas_avisa_diariamente_em_atraso(app, enviar):
    hoje = date.today()
    user, lista = _criar_user('util-atraso')
    _criar_tarefa(lista, user, 'Relatório atrasado', hoje - timedelta(days=3))

    pipe_tasks.tarefa_tarefas(hoje)
    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert 'atraso' in kw['subject'].lower()
    assert '3 dia' in kw['body']

    pipe_tasks.tarefa_tarefas(hoje + timedelta(days=1))   # dia seguinte
    assert enviar.call_count == 2


def test_tarefas_ignora_concluida_sem_prazo_e_futura(app, enviar):
    hoje = date.today()
    user, lista = _criar_user('util-ignora')
    _criar_tarefa(lista, user, 'Já feita', hoje, concluida=True)
    _criar_tarefa(lista, user, 'Sem prazo', None)
    _criar_tarefa(lista, user, 'Para amanhã', hoje + timedelta(days=1))

    pipe_tasks.tarefa_tarefas(hoje)

    assert enviar.call_count == 0


def test_tarefas_agrupa_utilizador_com_duas_secções(app, enviar):
    hoje = date.today()
    user_a, lista_a = _criar_user('util-misto')
    user_b, lista_b = _criar_user('util-simples')
    _criar_tarefa(lista_a, user_a, 'Hoje A', hoje)
    _criar_tarefa(lista_a, user_a, 'Ontem A', hoje - timedelta(days=1))
    _criar_tarefa(lista_b, user_b, 'Hoje B', hoje)

    pipe_tasks.tarefa_tarefas(hoje)

    assert enviar.call_count == 2
    por_user = _chamadas(enviar)
    kw_a = por_user['util-misto']
    assert 'Vencem hoje' in kw_a['body'] and 'Em atraso' in kw_a['body']
    assert kw_a['data'] == {'total_hoje': 1, 'total_atraso': 1}
    kw_b = por_user['util-simples']
    assert 'Vencem hoje' in kw_b['body'] and 'Em atraso' not in kw_b['body']


def test_calendario_avisa_dia_anterior(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-cal')
    amanha10 = (datetime.now() + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0)
    e = _criar_evento(user, amanha10, titulo='Reunião', localizacao='Escritório')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert kw['type'] == 'evento_lembrete'
    assert 'amanhã' in kw['subject'].lower()
    assert 'Reunião' in kw['body'] and 'Escritório' in kw['body']
    db.session.refresh(e)
    assert e.notificado_em == hoje


def test_calendario_avisa_no_dia(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-cal-hoje')
    e = _criar_evento(user, datetime.now() + timedelta(hours=2), titulo='Consulta')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert 'hoje' in kw['subject'].lower()
    assert 'Consulta' in kw['body']
    db.session.refresh(e)
    assert e.notificado_em == hoje


def test_calendario_sequencia_dois_avisos_sem_duplicar(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-sequencia')
    amanha10 = (datetime.now() + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0)
    e = _criar_evento(user, amanha10, titulo='Concerto')

    pipe_tasks.tarefa_calendario(hoje)                      # véspera → «Amanhã»
    pipe_tasks.tarefa_calendario(hoje + timedelta(days=1))  # dia do evento → «Hoje»
    pipe_tasks.tarefa_calendario(hoje + timedelta(days=2))  # depois → nada

    assert enviar.call_count == 2
    assert 'amanhã' in enviar.call_args_list[0].kwargs['subject'].lower()
    assert 'hoje' in enviar.call_args_list[1].kwargs['subject'].lower()
    db.session.refresh(e)
    assert e.notificado_em == hoje + timedelta(days=1)


def test_calendario_ignora_evento_ja_iniciado(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-iniciado')
    passado = datetime.now().replace(hour=0, minute=5, second=0, microsecond=0)
    _criar_evento(user, passado, titulo='Já passou')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 0


def test_calendario_inclui_dia_inteiro(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-dia-inteiro')
    meia_noite = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    _criar_evento(user, meia_noite, dia_inteiro=True, titulo='Aniversário')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 1
    kw = enviar.call_args_list[0].kwargs
    assert 'hoje' in kw['subject'].lower()
    assert 'dia inteiro' in kw['body']


def test_calendario_respeita_toggle_notificar(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-silencio')
    amanha10 = (datetime.now() + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0)
    _criar_evento(user, amanha10, notificar=False, titulo='Sigiloso')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 0


def test_calendario_ignora_eventos_antigos(app, enviar):
    hoje = date.today()
    user, _ = _criar_user('util-antigo')
    antigo = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) \
        - timedelta(days=7)
    _criar_evento(user, antigo, titulo='Evento velho')

    pipe_tasks.tarefa_calendario(hoje)

    assert enviar.call_count == 0
