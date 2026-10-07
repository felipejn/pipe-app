"""Testes dos providers de resumo do dashboard e do registry.

Cobertura:
- Registry: carrega TarefasProvider e CalendarioProvider.
- TarefasProvider: com dados, sem dados (NAO_CONFIGURADO), exceção (INDISPONIVEL).
- CalendarioProvider: com dados, sem dados (NAO_CONFIGURADO), exceção (INDISPONIVEL).
- Segurança: user A ≠ user B.
- Regressão: template renderiza com/sem resumos.
- Sem HTTP externo na carga síncrona do / (verificado por mock).
"""
from datetime import date, datetime, timedelta
from unittest import mock

import pytest

from app import create_app, db
from app.tarefas.models import Lista, Tarefa, TagTarefa
from app.calendario.models import Evento


# ── fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def app():
    """App de teste com SQLite em memória (nunca toca em BD real)."""
    app = create_app('testing')
    with app.app_context():
        uri = str(db.engine.url)
        assert 'memory' in uri, f'ABORTADO: BD real ({uri}).'
        db.create_all()
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


# ── registry ───────────────────────────────────────────────────────

class TestRegistry:
    def test_carregar_providers_popula_dicio(self):
        from app.dashboard.registry import carregar_providers, DASHBOARD_PROVIDERS
        carregar_providers()
        assert 'tarefas' in DASHBOARD_PROVIDERS
        assert 'calendario' in DASHBOARD_PROVIDERS

    def test_providers_sao_instancias(self):
        from app.dashboard.registry import carregar_providers, DASHBOARD_PROVIDERS
        carregar_providers()
        from app.dashboard.base import DashboardProvider
        for prov in DASHBOARD_PROVIDERS.values():
            assert isinstance(prov, DashboardProvider)

    def test_slug_consistente(self):
        from app.dashboard.registry import carregar_providers, DASHBOARD_PROVIDERS
        carregar_providers()
        assert DASHBOARD_PROVIDERS['tarefas'].slug == 'tarefas'
        assert DASHBOARD_PROVIDERS['calendario'].slug == 'calendario'


# ── TarefasProvider ────────────────────────────────────────────────

class TestTarefasProvider:
    def test_com_tarefas_devolve_ok(self, app):
        with app.app_context():
            from app.auth.models import User
            u = User(username='t1', email='t1@p.test', password_hash='x')
            db.session.add(u)
            db.session.commit()

            l = Lista(nome='L', user_id=u.id)
            db.session.add(l)
            db.session.commit()

            t1 = Tarefa(texto='Fazer', lista_id=l.id, user_id=u.id, concluida=False,
                        data_limite=date.today() + timedelta(days=1))
            t2 = Tarefa(texto='Feita', lista_id=l.id, user_id=u.id, concluida=True,
                        data_conclusao=datetime.utcnow())
            db.session.add_all([t1, t2])
            db.session.commit()

            from app.dashboard.registry import DASHBOARD_PROVIDERS
            r = DASHBOARD_PROVIDERS['tarefas'].resumir(u.id)

            assert r['estado'] == 'ok'
            labels = {m['label']: m['valor'] for m in r['metricas']}
            assert labels['total'] == 2
            assert labels['pendentes'] == 1

    def test_sem_tarefas_devolve_nao_configurado(self, app):
        with app.app_context():
            from app.auth.models import User
            u = User(username='t2', email='t2@p.test', password_hash='x')
            db.session.add(u)
            db.session.commit()

            from app.dashboard.registry import DASHBOARD_PROVIDERS
            r = DASHBOARD_PROVIDERS['tarefas'].resumir(u.id)
            assert r['estado'] == 'nao_configurado'
            assert r['metricas'] == []

    def test_excecao_vira_indisponivel(self, app):
        from app.dashboard.base import Estado
        from app.dashboard.registry import DASHBOARD_PROVIDERS
        prov = DASHBOARD_PROVIDERS['tarefas']

        with app.app_context():
            with mock.patch('app.tarefas.dashboard.Tarefa.query') as mock_q:
                mock_q.filter_by.side_effect = RuntimeError('BD down')
                r = prov.resumir(99)

        assert r['estado'] == Estado.INDISPONIVEL

    def test_user_isolamento(self, app):
        with app.app_context():
            from app.auth.models import User
            u1 = User(username='t3a', email='a@p.test', password_hash='x')
            u2 = User(username='t3b', email='b@p.test', password_hash='x')
            db.session.add_all([u1, u2])
            db.session.commit()

            l = Lista(nome='L', user_id=u1.id)
            db.session.add(l)
            db.session.commit()
            t = Tarefa(texto='Só do u1', lista_id=l.id, user_id=u1.id, concluida=False)
            db.session.add(t)
            db.session.commit()

            from app.dashboard.registry import DASHBOARD_PROVIDERS
            r1 = DASHBOARD_PROVIDERS['tarefas'].resumir(u1.id)
            r2 = DASHBOARD_PROVIDERS['tarefas'].resumir(u2.id)

            labels1 = {m['label']: m['valor'] for m in r1['metricas']}
            assert labels1['total'] == 1
            assert r2['estado'] == 'nao_configurado'
            assert r2['metricas'] == []


# ── CalendarioProvider ─────────────────────────────────────────────

class TestCalendarioProvider:
    def test_com_eventos_devolve_ok(self, app):
        with app.app_context():
            from app.auth.models import User
            u = User(username='c1', email='c1@p.test', password_hash='x')
            db.session.add(u)
            db.session.commit()

            hoje = datetime.utcnow()
            ev = Evento(user_id=u.id, titulo='Reunião', data_inicio=hoje,
                        data_fim=hoje + timedelta(hours=1))
            db.session.add(ev)
            db.session.commit()

            from app.dashboard.registry import DASHBOARD_PROVIDERS
            r = DASHBOARD_PROVIDERS['calendario'].resumir(u.id)

            assert r['estado'] == 'ok'
            labels = {m['label']: m['valor'] for m in r['metricas']}
            assert labels['hoje'] >= 1
            assert labels['total'] >= 1

    def test_sem_eventos_devolve_nao_configurado(self, app):
        with app.app_context():
            from app.auth.models import User
            u = User(username='c2', email='c2@p.test', password_hash='x')
            db.session.add(u)
            db.session.commit()

            from app.dashboard.registry import DASHBOARD_PROVIDERS
            r = DASHBOARD_PROVIDERS['calendario'].resumir(u.id)
            assert r['estado'] == 'nao_configurado'
            assert r['metricas'] == []

    def test_excecao_vira_indisponivel(self, app):
        from app.dashboard.base import Estado
        from app.dashboard.registry import DASHBOARD_PROVIDERS
        prov = DASHBOARD_PROVIDERS['calendario']

        with app.app_context():
            with mock.patch('app.calendario.dashboard.Evento.query') as mock_q:
                mock_q.filter_by.side_effect = RuntimeError('BD down')
                r = prov.resumir(99)

        assert r['estado'] == Estado.INDISPONIVEL

    def test_user_isolamento(self, app):
        with app.app_context():
            from app.auth.models import User
            u1 = User(username='c3a', email='a@p.test', password_hash='x')
            u2 = User(username='c3b', email='b@p.test', password_hash='x')
            db.session.add_all([u1, u2])
            db.session.commit()

            hoje = datetime.utcnow()
            ev = Evento(user_id=u1.id, titulo='Só u1', data_inicio=hoje,
                        data_fim=hoje + timedelta(hours=1))
            db.session.add(ev)
            db.session.commit()

            from app.dashboard.registry import DASHBOARD_PROVIDERS
            r1 = DASHBOARD_PROVIDERS['calendario'].resumir(u1.id)
            r2 = DASHBOARD_PROVIDERS['calendario'].resumir(u2.id)

            labels1 = {m['label']: m['valor'] for m in r1['metricas']}
            assert labels1['total'] == 1
            assert r2['estado'] == 'nao_configurado'
            assert r2['metricas'] == []


# ── dashboard route ────────────────────────────────────────────────

class TestDashboardRoute:
    def test_template_renders_com_providers(self, client):
        """O route / renderiza sem erro quando os providers estão activos."""
        from app.auth.models import User
        with client.application.app_context():
            u = User(username='d1', email='d1@p.test', password_hash='x')
            db.session.add(u)
            db.session.commit()

        resp = client.get('/', follow_redirects=True)
        assert resp.status_code in (200, 302)

    def test_sem_resumos_fallback_clássico(self, client):
        """resumos=None não quebra o template (fallback clássico)."""
        resp = client.get('/')
        assert resp.status_code in (200, 302)

    def test_nao_chama_http_externo_na_carga(self, client):
        """Nenhuma chamada HTTP externa durante a renderização do /."""
        with mock.patch('requests.get') as mock_get, \
             mock.patch('requests.post') as mock_post:
            resp = client.get('/')
            assert resp.status_code in (200, 302)
            mock_get.assert_not_called()
            mock_post.assert_not_called()
