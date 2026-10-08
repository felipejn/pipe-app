"""Invariante do registo de ferramentas do Assistente IA + regressao criar_tarefa.

Garante que nunca mais acontece o incidente de v1.7.2 (commit 0072033), em
que a adicao de `get_meteorologia` ao REGISTO_FERRAMENTAS substituiu por
engano a linha de `criar_tarefa`: a ferramenta continuava anunciada ao LLM
(DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA) mas o despachante devolvia
"Ferramenta desconhecida".

Os testes de invariante cruzam as tres estruturas — definicoes JSON
anunciadas ao modelo, mapa nome->funcao e conjunto de escrita — nos dois
sentidos, sem tocar na BD. Os testes de regressao exercem `criar_tarefa`
de ponta a ponta (modo escrita cria; modo leitura bloqueia).

Usam SQLite em memoria (create_app('testing')), sem tocar na BD real.
"""

from unittest import TestCase

import app.assistente.ferramentas as ferramentas_mod
from app import create_app, db
from app.assistente.ferramentas import (
    DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA,
    DEFINICOES_FERRAMENTAS_LEITURA,
    FERRAMENTAS_ESCRITA,
    REGISTO_FERRAMENTAS,
    executar_ferramenta,
)
from app.auth.models import User
from app.tarefas.models import Tarefa


def _nomes_definicoes():
    """Todos os nomes anunciados ao LLM (leitura + escrita)."""
    return [
        d['function']['name']
        for d in DEFINICOES_FERRAMENTAS_LEITURA + DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA
    ]


class InvarianteRegistoTests(TestCase):
    """As tres estruturas tem de estar consistentes nos dois sentidos."""

    def test_toda_definicao_anunciada_tem_registo(self):
        """Cada ferramenta anunciada ao LLM tem entrada no despachante."""
        em_falta = [n for n in _nomes_definicoes() if n not in REGISTO_FERRAMENTAS]
        self.assertEqual(em_falta, [])

    def test_todo_registo_tem_definicao_anunciada(self):
        """Cada entrada do despachante corresponde a ferramenta anunciada."""
        nomes = set(_nomes_definicoes())
        sem_definicao = [n for n in REGISTO_FERRAMENTAS if n not in nomes]
        self.assertEqual(sem_definicao, [])

    def test_todo_registo_aponta_para_funcao_existente(self):
        """Cada valor do mapa e o nome de uma funcao chamavel do modulo."""
        for nome, func_nome in REGISTO_FERRAMENTAS.items():
            with self.subTest(ferramenta=nome):
                func = getattr(ferramentas_mod, func_nome, None)
                self.assertTrue(callable(func))

    def test_conjunto_escrita_coincide_com_definicoes_extra(self):
        """FERRAMENTAS_ESCRITA tem exactamente as ferramentas de escrita."""
        nomes_extra = {d['function']['name'] for d in DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA}
        self.assertEqual(FERRAMENTAS_ESCRITA, nomes_extra)

    def test_sem_nomes_repetidos_entre_leitura_e_escrita(self):
        """Nenhuma ferramenta pode estar definida nos dois grupos."""
        nomes_leitura = {d['function']['name'] for d in DEFINICOES_FERRAMENTAS_LEITURA}
        nomes_extra = {d['function']['name'] for d in DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA}
        self.assertEqual(nomes_leitura & nomes_extra, set())


class CriarTarefaRegressaoTests(TestCase):
    """Regressao do incidente v1.7.2: criar_tarefa tem de despachar e criar."""

    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = User(username='reguser', email='reguser@pipe.local',
                         password_hash='x')
        db.session.add(self.user)
        db.session.commit()
        self.user_id = self.user.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_criar_tarefa_registada(self):
        self.assertIn('criar_tarefa', REGISTO_FERRAMENTAS)

    def test_criar_tarefa_executa_em_modo_escrita(self):
        with self.app.test_request_context('/assistente'):
            resultado = executar_ferramenta(
                'criar_tarefa', {'texto': 'Regressao do registo'},
                self.user_id, modo='escrita')
        self.assertTrue(resultado.get('ok'))
        tarefa = Tarefa.query.filter_by(id=resultado['id'],
                                        user_id=self.user_id).first()
        self.assertIsNotNone(tarefa)
        self.assertEqual(tarefa.texto, 'Regressao do registo')

    def test_criar_tarefa_bloqueada_em_modo_leitura(self):
        with self.app.test_request_context('/assistente'):
            resultado = executar_ferramenta(
                'criar_tarefa', {'texto': 'Nao deve ser criada'},
                self.user_id, modo='leitura')
        self.assertIn('erro', resultado)
        self.assertIsNone(Tarefa.query.filter_by(
            texto='Nao deve ser criada', user_id=self.user_id).first())
