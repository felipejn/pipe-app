"""Regressões para consultas semanais do Assistente PIPE."""

import json
from datetime import date, datetime, timezone
from unittest import TestCase, mock

from app import create_app, db
from app.assistente.contexto import (
    _serializar_resultado_tool,
    processar_mensagem_assistente,
)
from app.assistente.ferramentas import (
    DEFINICOES_FERRAMENTAS_LEITURA,
    _dia_semana_evento,
    calcular_intervalo_semana,
    criar_evento,
    get_eventos,
    get_tarefas,
)
from app.auth.models import User
from app.calendario.models import Evento
from app.tarefas.models import Lista, Tarefa


class ConsultasSemanaTests(TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = User(username='semana', email='semana@pipe.local', password_hash='x')
        db.session.add(self.user)
        db.session.flush()
        self.lista = Lista(nome='Pessoal', user_id=self.user.id)
        db.session.add(self.lista)
        db.session.flush()

        # 19 tarefas no total, apenas uma pendente; duas têm prazo nesta semana.
        for i in range(19):
            if i == 0:
                prazo, concluida = date(2026, 10, 17), False
            elif i == 1:
                prazo, concluida = date(2026, 10, 14), True
            elif i == 2:
                prazo, concluida = None, True
            else:
                prazo, concluida = date(2026, 9, 1), True
            db.session.add(Tarefa(
                texto=f'Tarefa {i + 1}', concluida=concluida,
                data_limite=prazo, lista_id=self.lista.id, user_id=self.user.id,
            ))

        # Um evento que atravessa o início da semana, um que atravessa o fim
        # e outro na semana seguinte.
        db.session.add_all([
            Evento(user_id=self.user.id, titulo='Cruza início',
                   data_inicio=datetime(2026, 10, 11, 23),
                   data_fim=datetime(2026, 10, 12, 1)),
            Evento(user_id=self.user.id, titulo='Cruza fim',
                   data_inicio=datetime(2026, 10, 18, 23),
                   data_fim=datetime(2026, 10, 19, 1)),
            Evento(user_id=self.user.id, titulo='Semana seguinte',
                   data_inicio=datetime(2026, 10, 22, 15),
                   data_fim=datetime(2026, 10, 22, 16)),
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_semana_actual_num_domingo_comeca_na_segunda_anterior(self):
        self.assertEqual(
            calcular_intervalo_semana(date(2026, 10, 18)),
            (date(2026, 10, 12), date(2026, 10, 18)),
        )

    def test_data_22_outubro_2026_e_quinta_feira(self):
        self.assertEqual(
            _dia_semana_evento(datetime(2026, 10, 22, 15)),
            'quinta-feira',
        )

    def test_evento_com_hora_utc_e_convertido_para_dia_local_de_lisboa(self):
        instante = datetime(2026, 10, 21, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(_dia_semana_evento(instante), 'quinta-feira')

    def test_criar_evento_guarda_hora_de_lisboa_e_semana_correcta(self):
        criado = criar_evento(
            self.user.id, 'Fronteira semanal',
            '2026-10-18T23:30:00+00:00', '2026-10-19T00:30:00+00:00',
        )
        evento = db.session.get(Evento, criado['id'])

        self.assertEqual(evento.data_inicio, datetime(2026, 10, 19, 0, 30))
        self.assertEqual(evento.data_fim, datetime(2026, 10, 19, 1, 30))
        semana_seguinte = get_eventos(
            self.user.id, data_inicio='2026-10-19', data_fim='2026-10-25'
        )
        semana_anterior = get_eventos(
            self.user.id, data_inicio='2026-10-12', data_fim='2026-10-18'
        )
        self.assertIn('Fronteira semanal',
                      {e['titulo'] for e in semana_seguinte['eventos']})
        self.assertNotIn('Fronteira semanal',
                         {e['titulo'] for e in semana_anterior['eventos']})

    def test_filtro_semanal_de_tarefas_preserva_total_e_estado_correctos(self):
        abertas = get_tarefas(self.user.id)
        todas = get_tarefas(self.user.id, estado='todas')
        with mock.patch('app.assistente.ferramentas.calcular_intervalo_semana',
                        return_value=(date(2026, 10, 12), date(2026, 10, 18))):
            semana = get_tarefas(self.user.id, esta_semana=True)

        self.assertEqual(abertas['total'], 1)
        self.assertEqual({t['titulo'] for t in abertas['tarefas']}, {'Tarefa 1'})
        self.assertEqual(todas['total'], 19)
        self.assertEqual(todas['pendentes'], 1)
        self.assertEqual(semana['total'], 1)
        self.assertEqual(semana['pendentes'], 1)
        self.assertEqual(semana['concluidas'], 0)
        self.assertEqual(semana['intervalo'], {
            'inicio': '2026-10-12', 'fim': '2026-10-18',
        })
        self.assertEqual({t['titulo'] for t in semana['tarefas']},
                         {'Tarefa 1'})

    def test_filtro_semanal_de_eventos_inclui_sobreposicoes_e_dia_calculado(self):
        with mock.patch('app.assistente.ferramentas.calcular_intervalo_semana',
                        return_value=(date(2026, 10, 12), date(2026, 10, 18))):
            semana = get_eventos(self.user.id, esta_semana=True)

        self.assertEqual(semana['total'], 2)
        self.assertEqual([e['titulo'] for e in semana['eventos']],
                         ['Cruza início', 'Cruza fim'])
        self.assertEqual(semana['eventos'][0]['dia_semana'], 'domingo')
        self.assertEqual(semana['eventos'][1]['dia_semana'], 'domingo')
        self.assertEqual(semana['intervalo'], {
            'inicio': '2026-10-12', 'fim': '2026-10-18',
        })

    def test_intervalo_explicito_de_tarefas_e_eventos_e_validado(self):
        erro_tarefas = get_tarefas(
            self.user.id, data_inicio='2026-10-19', data_fim='2026-10-12'
        )
        erro_eventos = get_eventos(self.user.id, data_inicio='2026-10-12')

        self.assertIn('erro', erro_tarefas)
        self.assertIn('erro', erro_eventos)

    def test_esquemas_de_ferramentas_expoem_filtro_semanal(self):
        esquemas = {
            item['function']['name']: item['function']['parameters']['properties']
            for item in DEFINICOES_FERRAMENTAS_LEITURA
        }
        for nome in ('get_tarefas', 'get_eventos'):
            self.assertIn('esta_semana', esquemas[nome])
            self.assertIn('data_inicio', esquemas[nome])
            self.assertIn('data_fim', esquemas[nome])

    def test_resultado_lista_truncado_indica_total_e_incompletude(self):
        dados = json.loads(_serializar_resultado_tool(list(range(19))))

        self.assertEqual(len(dados['itens']), 10)
        self.assertEqual(dados['total'], 19)
        self.assertTrue(dados['truncado'])

    @mock.patch('app.assistente.routes.processar_mensagem_assistente')
    def test_endpoint_limita_tamanho_das_instrucoes_enviadas(self, processar):
        processar.return_value = ('ok', 'modelo')
        cliente = self.app.test_client()
        with cliente.session_transaction() as sessao:
            sessao['_user_id'] = str(self.user.id)
            sessao['_fresh'] = True

        resposta = cliente.post('/assistente/api/chat', json={
            'mensagem': 'x' * 3001,
        })

        self.assertEqual(resposta.status_code, 413)
        processar.assert_not_called()

    def test_endpoint_calendario_guarda_datas_com_offset_em_hora_local(self):
        cliente = self.app.test_client()
        with cliente.session_transaction() as sessao:
            sessao['_user_id'] = str(self.user.id)
            sessao['_fresh'] = True

        resposta = cliente.post('/calendario/api/eventos', json={
            'titulo': 'Evento via API',
            'data_inicio': '2026-10-18T23:30:00+00:00',
            'data_fim': '2026-10-19T00:30:00+00:00',
        })
        evento = db.session.get(Evento, resposta.json['id'])

        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(evento.data_inicio, datetime(2026, 10, 19, 0, 30))
        self.assertEqual(evento.data_fim, datetime(2026, 10, 19, 1, 30))

    @mock.patch('app.assistente.contexto.chamar_llm')
    def test_agenda_semanal_e_composta_sem_pedir_ao_modelo_dias_ou_contagens(self, chamar):
        historico = []
        with mock.patch('app.assistente.contexto._data_actual',
                        return_value=date(2026, 10, 18)), \
             mock.patch('app.assistente.contexto.calcular_intervalo_semana',
                        return_value=(date(2026, 10, 12), date(2026, 10, 18))), \
             mock.patch('app.assistente.ferramentas.calcular_intervalo_semana',
                        return_value=(date(2026, 10, 12), date(2026, 10, 18))):
            resposta, historico, _ = processar_mensagem_assistente(
                'Lista os compromissos e tarefas desta semana',
                user_id=self.user.id, historico=historico, modo='leitura',
            )

        chamar.assert_not_called()
        self.assertIn('12/10/2026 a 18/10/2026', resposta)
        self.assertIn('Total geral: 1 tarefa(s) em aberto.', resposta)
        self.assertIn('1 tarefa(s) em aberto no intervalo.', resposta)
        self.assertIn('Cruza fim', resposta)
        self.assertIn('segunda-feira, 19/10/2026', resposta)
        self.assertNotIn('Semana seguinte', resposta)
        self.assertNotIn('Tarefa 2', resposta)
        self.assertNotIn('22 de outubro (2ª-feira)', resposta)
        self.assertEqual(historico[-1]['content'], resposta)
