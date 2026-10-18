"""Testes das ferramentas de edicao de tarefas e eventos pelo Assistente."""

from datetime import date, datetime
from unittest import TestCase

from app import create_app, db
from app.assistente.ferramentas import (
    DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA,
    FERRAMENTAS_ESCRITA,
    REGISTO_FERRAMENTAS,
    executar_ferramenta,
)
from app.assistente.contexto import SYSTEM_PROMPT_ESCRITA
from app.auth.models import User
from app.calendario.models import Evento
from app.tarefas.models import Lista, TagTarefa, Tarefa


class EdicaoAssistenteTests(TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = User(username='editor', email='editor@pipe.local', password_hash='x')
        self.outro = User(username='outro', email='outro@pipe.local', password_hash='x')
        db.session.add_all([self.user, self.outro])
        db.session.flush()
        self.lista = Lista(nome='Pessoal', user_id=self.user.id)
        self.lista_outro = Lista(nome='Pessoal', user_id=self.outro.id)
        db.session.add_all([self.lista, self.lista_outro])
        db.session.flush()
        self.tarefa = Tarefa(
            texto='Original', prioridade='baixa', data_limite=date(2026, 10, 20),
            notas='Nota original', lista_id=self.lista.id, user_id=self.user.id,
            notificada_em=date(2026, 10, 18),
        )
        self.evento = Evento(
            user_id=self.user.id, titulo='Original',
            data_inicio=datetime(2026, 10, 20, 10),
            data_fim=datetime(2026, 10, 20, 11),
            descricao='Descrição original', localizacao='Braga',
            notificado_em=date(2026, 10, 18),
        )
        db.session.add_all([self.tarefa, self.evento])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _executar(self, nome, argumentos):
        with self.app.test_request_context('/assistente'):
            return executar_ferramenta(nome, argumentos, self.user.id, modo='escrita')

    def test_atualizar_tarefa_fica_registada_e_disponivel_em_escrita(self):
        definicoes = {
            item['function']['name']: item
            for item in DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA
        }
        self.assertIn('atualizar_tarefa', definicoes)
        self.assertIn('atualizar_tarefa', REGISTO_FERRAMENTAS)
        self.assertIn('atualizar_tarefa', FERRAMENTAS_ESCRITA)
        schema = definicoes['atualizar_tarefa']['function']['parameters']['properties']
        self.assertEqual(schema['data_limite']['type'], ['string', 'null'])

    def test_edicao_parcial_preserva_campos_omitidos_e_reabre_notificacao(self):
        resultado = self._executar('atualizar_tarefa', {
            'tarefa_id': self.tarefa.id, 'texto': 'Actualizada', 'data_limite': '2026-10-25',
        })
        db.session.refresh(self.tarefa)
        self.assertTrue(resultado.get('ok'))
        self.assertEqual(self.tarefa.texto, 'Actualizada')
        self.assertEqual(self.tarefa.prioridade, 'baixa')
        self.assertEqual(self.tarefa.notas, 'Nota original')
        self.assertEqual(self.tarefa.data_limite, date(2026, 10, 25))
        self.assertIsNone(self.tarefa.notificada_em)

    def test_prazo_nulo_remove_prazo_e_omissao_preserva(self):
        self._executar('atualizar_tarefa', {'tarefa_id': self.tarefa.id})
        self.assertEqual(self.tarefa.data_limite, date(2026, 10, 20))
        resultado = self._executar('atualizar_tarefa', {
            'tarefa_id': self.tarefa.id, 'data_limite': None,
        })
        db.session.refresh(self.tarefa)
        self.assertTrue(resultado.get('ok'))
        self.assertIsNone(self.tarefa.data_limite)
        self.assertIsNone(self.tarefa.notificada_em)

    def test_tags_omitidas_preservam_e_vazias_limpa(self):
        tag = TagTarefa(nome='urgente', user_id=self.user.id)
        db.session.add(tag)
        db.session.flush()
        self.tarefa.tags = [tag]
        db.session.commit()
        self._executar('atualizar_tarefa', {'tarefa_id': self.tarefa.id})
        self.assertEqual([t.nome for t in self.tarefa.tags], ['urgente'])
        self._executar('atualizar_tarefa', {'tarefa_id': self.tarefa.id, 'tags': ''})
        self.assertEqual(self.tarefa.tags, [])

    def test_atualizacao_valida_lista_do_utilizador_e_campos_editaveis(self):
        resultado = self._executar('atualizar_tarefa', {
            'tarefa_id': self.tarefa.id, 'prioridade': 'alta', 'notas': '',
            'lista_nome': 'Pessoal', 'tags': 'casa, urgente',
        })
        db.session.refresh(self.tarefa)
        self.assertTrue(resultado.get('ok'))
        self.assertEqual(self.tarefa.prioridade, 'alta')
        self.assertIsNone(self.tarefa.notas)
        self.assertEqual(self.tarefa.lista_id, self.lista.id)
        self.assertEqual({t.nome for t in self.tarefa.tags}, {'casa', 'urgente'})

    def test_argumentos_invalidos_nao_gravam_nem_criam_tags(self):
        antes = (self.tarefa.texto, self.tarefa.prioridade, self.tarefa.data_limite)
        for argumentos in (
            {'prioridade': 'urgente'},
            {'data_limite': '2026-02-30'},
            {'texto': 'x' * 513},
            {'notas': 'x' * 1001},
            {'tags': 'x' * 257},
            {'lista_nome': 'Inexistente'},
        ):
            with self.subTest(argumentos=argumentos):
                resultado = self._executar('atualizar_tarefa', {
                    'tarefa_id': self.tarefa.id, 'texto': 'Alteração parcial', **argumentos,
                })
                self.assertIn('erro', resultado)
                db.session.refresh(self.tarefa)
                self.assertEqual((self.tarefa.texto, self.tarefa.prioridade,
                                  self.tarefa.data_limite), antes)
                self.assertIsNone(TagTarefa.query.filter_by(
                    nome='casa', user_id=self.user.id).first())

    def test_tarefa_de_outro_utilizador_nao_e_actualizada(self):
        tarefa_alheia = Tarefa(
            texto='Privada', prioridade='media', lista_id=self.lista_outro.id,
            user_id=self.outro.id,
        )
        db.session.add(tarefa_alheia)
        db.session.commit()
        with self.app.test_request_context('/assistente'):
            resultado = executar_ferramenta(
                'atualizar_tarefa', {'tarefa_id': tarefa_alheia.id, 'texto': 'Não permitido'},
                self.user.id, modo='escrita',
            )
        self.assertIn('erro', resultado)
        db.session.refresh(tarefa_alheia)
        self.assertEqual(tarefa_alheia.texto, 'Privada')

    def test_atualizar_tarefa_bloqueada_em_modo_leitura(self):
        with self.app.test_request_context('/assistente'):
            resultado = executar_ferramenta(
                'atualizar_tarefa', {'tarefa_id': self.tarefa.id, 'texto': 'x'},
                self.user.id, modo='leitura',
            )
        self.assertIn('erro', resultado)
        self.assertEqual(self.tarefa.texto, 'Original')

    def test_prompt_orienta_consulta_id_e_actualizacao_parcial(self):
        prompt = SYSTEM_PROMPT_ESCRITA.lower()
        self.assertIn('consulta primeiro get_tarefas/get_eventos', prompt)
        self.assertIn('data_limite=null', prompt)
        self.assertIn('data_inicio e data_fim coerentes', prompt)

    def test_evento_aceita_actualizacao_parcial_e_limpeza_de_texto(self):
        resultado = self._executar('atualizar_evento', {
            'evento_id': self.evento.id, 'descricao': '', 'localizacao': None,
        })
        db.session.refresh(self.evento)
        self.assertTrue(resultado.get('ok'))
        self.assertIsNone(self.evento.descricao)
        self.assertIsNone(self.evento.localizacao)
        self.assertEqual(self.evento.titulo, 'Original')
        self.assertIsNone(self.evento.notificado_em)

    def test_evento_com_datas_com_fuso_e_normalizado_para_hora_local(self):
        resultado = self._executar('atualizar_evento', {
            'evento_id': self.evento.id,
            'data_inicio': '2026-10-20T12:00:00+02:00',
            'data_fim': '2026-10-20T14:00:00+02:00',
        })
        db.session.refresh(self.evento)
        self.assertTrue(resultado.get('ok'))
        self.assertEqual(self.evento.data_inicio, datetime(2026, 10, 20, 11))
        self.assertEqual(self.evento.data_fim, datetime(2026, 10, 20, 13))

    def test_evento_invalido_nao_grava_nenhum_campo(self):
        resultado = self._executar('atualizar_evento', {
            'evento_id': self.evento.id, 'titulo': 'Alterado',
            'data_inicio': '2026-10-21T13:00:00',
        })
        db.session.refresh(self.evento)
        self.assertIn('erro', resultado)
        self.assertEqual(self.evento.titulo, 'Original')
        self.assertEqual(self.evento.data_inicio, datetime(2026, 10, 20, 10))
        self.assertEqual(self.evento.notificado_em, date(2026, 10, 18))

    def test_evento_de_outro_utilizador_nao_e_actualizado(self):
        evento_alheio = Evento(
            user_id=self.outro.id, titulo='Privado',
            data_inicio=datetime(2026, 10, 20, 10),
            data_fim=datetime(2026, 10, 20, 11),
        )
        db.session.add(evento_alheio)
        db.session.commit()
        with self.app.test_request_context('/assistente'):
            resultado = executar_ferramenta(
                'atualizar_evento', {'evento_id': evento_alheio.id, 'titulo': 'Intrusão'},
                self.user.id, modo='escrita',
            )
        self.assertIn('erro', resultado)
        db.session.refresh(evento_alheio)
        self.assertEqual(evento_alheio.titulo, 'Privado')

    def test_cor_invalida_nao_grava_mudancas_parciais(self):
        resultado = self._executar('atualizar_evento', {
            'evento_id': self.evento.id, 'titulo': 'Alterado', 'cor': 'ultravioleta',
        })
        db.session.refresh(self.evento)
        self.assertIn('erro', resultado)
        self.assertEqual(self.evento.titulo, 'Original')
