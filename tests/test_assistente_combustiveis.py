"""Testes unitários da ferramenta get_combustiveis do Assistente IA.

Cobrem o contrato da ferramenta com o modelo: filtros, validação dos
argumentos, isolamento por utilizador (concelhos) e formato da resposta.
Usam SQLite em memória, sem tocar na BD real nem na API Aberta.
"""

from datetime import datetime
from unittest import TestCase

from app import create_app, db
from app.assistente.ferramentas import (
    DEFINICOES_FERRAMENTAS_LEITURA,
    REGISTO_FERRAMENTAS,
    executar_ferramenta,
    get_combustiveis,
)
from app.auth.models import User
from app.combustiveis.models import (
    EstadoAtualizacaoCombustiveis,
    Posto,
    PrecoHistorico,
    UtilizadorCombustivel,
    UtilizadorConcelho,
)


class _BaseCombustiveis(TestCase):
    """Cria uma app isolada com SQLite em memória e dados de teste."""

    def setUp(self):
        # Toda a config de teste (SQLite em memória, CSRF desligado, sessões
        # temporárias) vem do TestingConfig: atribuir app.config depois de
        # create_app() não tem efeito e leva os testes a usar a BD real.
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.user = User(username='tester', email='tester@pipe.local',
                         password_hash='x')
        db.session.add(self.user)
        db.session.flush()
        self.user_id = self.user.id

        self.outro_user = User(username='outro', email='outro@pipe.local',
                               password_hash='x')
        db.session.add(self.outro_user)
        db.session.flush()

        # Posto barato em Vila Verde e posto caro em Braga — o segundo só deve
        # aparecer se o utilizador tiver Braga nos seus concelhos.
        self.posto_vv = self._criar_posto(1, 'PD VILA VERDE', 'PINGO DOCE', 'Vila Verde')
        self.posto_braga = self._criar_posto(2, 'Bxpress Braga', 'BXPRESS', 'Braga')
        self._criar_preco(self.posto_vv, 'Gasóleo simples', 2.113)
        self._criar_preco(self.posto_braga, 'Gasóleo simples', 2.049)
        self._criar_preco(self.posto_braga, 'Gasolina simples 95', 1.959)

        db.session.add(UtilizadorConcelho(user_id=self.user_id, concelho='Vila Verde'))
        db.session.add(UtilizadorCombustivel(user_id=self.user_id,
                                             tipo_combustivel='Gasóleo simples'))
        # A linha id=1 já é criada pelo create_app() — reutiliza-se e só se
        # preenchem os campos de estado, para não violar a PK.
        estado = EstadoAtualizacaoCombustiveis.query.get(1)
        if estado is None:
            estado = EstadoAtualizacaoCombustiveis(id=1)
            db.session.add(estado)
        estado.ultima_atualizacao = datetime(2026, 9, 18, 14, 46)
        estado.ultima_execucao_sucesso = True
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    # ── Helpers ──────────────────────────────────────────────────────────

    def _criar_posto(self, posto_id, nome, marca, concelho):
        posto = Posto(id=posto_id, nome=nome, marca=marca, concelho=concelho,
                      ativo=True, ciclos_ausente=0)
        db.session.add(posto)
        db.session.flush()
        return posto

    def _criar_preco(self, posto, tipo, preco, dgeg='2026-09-18T06:30:25.479Z'):
        registo = PrecoHistorico(
            posto_id=posto.id, tipo_combustivel=tipo, preco=preco,
            data_atualizacao_dgeg=dgeg, data_recolha=datetime(2026, 9, 18, 13, 28),
        )
        db.session.add(registo)
        db.session.flush()
        return registo


class RegistoFerramentaTests(_BaseCombustiveis):
    """A ferramenta tem de estar registada nos dois sentidos."""

    def test_registada_no_registo_e_nas_definicoes_de_leitura(self):
        self.assertIn('get_combustiveis', REGISTO_FERRAMENTAS)
        nomes = [d['function']['name'] for d in DEFINICOES_FERRAMENTAS_LEITURA]
        self.assertIn('get_combustiveis', nomes)

    def test_nao_e_bloqueada_em_modo_consulta(self):
        """É de leitura: em modo consulta tem de executar, nunca ser bloqueada."""
        resultado = executar_ferramenta('get_combustiveis', {}, self.user_id,
                                        modo='leitura')
        self.assertNotIn('erro', resultado)


class SemConcelhosTests(_BaseCombustiveis):
    """Sem concelhos escolhidos, o modelo tem de ser encaminhado para o módulo."""

    def test_utilizador_sem_concelhos_devolve_erro_orientador(self):
        resultado = get_combustiveis(self.outro_user.id)
        self.assertIn('erro', resultado)
        self.assertIn('Combustíveis → Definições', resultado['erro'])

    def test_concelhos_de_outro_utilizador_nao_sao_visiveis(self):
        """Isolamento: o posto de Braga pertence aos concelhos de outro utilizador."""
        db.session.add(UtilizadorConcelho(user_id=self.outro_user.id, concelho='Braga'))
        db.session.commit()

        resultado = get_combustiveis(self.outro_user.id)
        concelhos_vistos = {p['concelho'] for p in resultado['precos']}
        self.assertEqual(concelhos_vistos, {'Braga'})
        self.assertNotIn('Vila Verde', concelhos_vistos)


class FiltrosTests(_BaseCombustiveis):
    def test_sem_argumentos_devolve_apenas_os_concelhos_do_utilizador(self):
        resultado = get_combustiveis(self.user_id)
        self.assertEqual(resultado['concelhos'], ['Vila Verde'])
        self.assertEqual(resultado['total'], len(resultado['precos']))
        for preco in resultado['precos']:
            self.assertEqual(preco['concelho'], 'Vila Verde')
            self.assertNotEqual(preco['posto'], 'Bxpress Braga')

    def test_filtro_de_combustivel_ignora_acentos_e_caixa(self):
        """O modelo escreve muitas vezes 'gasoleo simples' sem acento."""
        resultado = get_combustiveis(self.user_id, tipo_combustivel='gasoleo simples')
        self.assertNotIn('erro', resultado)
        self.assertEqual(resultado['tipos_combustivel'], ['Gasóleo simples'])

    def test_filtro_todos_equivale_a_sem_filtro(self):
        sem_filtro = get_combustiveis(self.user_id)
        com_todos = get_combustiveis(self.user_id, tipo_combustivel='Todos')
        self.assertEqual(sem_filtro['total'], com_todos['total'])

    def test_combustivel_fora_do_universo_explica_os_disponiveis(self):
        resultado = get_combustiveis(self.user_id, tipo_combustivel='Hidrogénio')
        self.assertIn('erro', resultado)
        self.assertIn('Gasóleo simples', resultado['erro'])
        self.assertIn('Definições', resultado['erro'])

    def test_concelho_de_outro_utilizador_e_rejeitado(self):
        """Braga existe na BD, mas não nos concelhos deste utilizador."""
        resultado = get_combustiveis(self.user_id, concelho='Braga')
        self.assertIn('erro', resultado)
        self.assertIn('Vila Verde', resultado['erro'])

    def test_concelho_sem_postos_nao_e_confundido_com_concelho_desconhecido(self):
        db.session.add(UtilizadorConcelho(user_id=self.user_id, concelho='Amares'))
        db.session.commit()

        resultado = get_combustiveis(self.user_id, concelho='amares')
        self.assertIn('erro', resultado)  # Amares não tem postos de teste
        self.assertNotIn('não está nos teus concelhos', resultado['erro'])


class MaisBaratoTests(_BaseCombustiveis):
    def test_apenas_mais_barato_devolve_minimo_por_combustivel(self):
        db.session.add(UtilizadorCombustivel(user_id=self.user_id,
                                             tipo_combustivel='Gasolina simples 95'))
        db.session.add(UtilizadorConcelho(user_id=self.user_id, concelho='Braga'))
        db.session.commit()

        resultado = get_combustiveis(self.user_id, apenas_mais_barato=True)
        self.assertNotIn('erro', resultado)
        baratos = {m['tipo_combustivel']: m
                   for m in resultado['mais_barato_por_combustivel']}
        self.assertEqual(sorted(baratos), sorted(['Gasóleo simples', 'Gasolina simples 95']))
        self.assertEqual(baratos['Gasóleo simples']['preco'], 2.049)
        self.assertEqual(baratos['Gasóleo simples']['posto'], 'Bxpress Braga')
        self.assertEqual(baratos['Gasolina simples 95']['preco'], 1.959)
        self.assertNotIn('precos', resultado)


class LimiteTests(_BaseCombustiveis):
    def test_limite_trunca_e_assinala(self):
        resultado = get_combustiveis(self.user_id, limite=1)
        self.assertEqual(len(resultado['precos']), 1)
        # Só há 1 preço nos concelhos deste utilizador — para exercitar o
        # truncamento é preciso haver mais do que o limite.
        self.assertNotIn('truncado', resultado)

    def test_limite_abaixo_do_total_trunca_e_assinala(self):
        for preco in (2.114, 2.115, 2.169):
            self._criar_preco(self.posto_vv, 'Gasóleo simples', preco)
        db.session.commit()

        resultado = get_combustiveis(self.user_id, limite=2)
        self.assertEqual(len(resultado['precos']), 2)
        self.assertEqual(resultado['total'], 4)
        self.assertTrue(resultado['truncado'])
        self.assertIn('2 de 4', resultado['nota'])

    def test_limite_invalido_cai_no_default(self):
        resultado = get_combustiveis(self.user_id, limite='abc')
        self.assertNotIn('erro', resultado)
        self.assertNotIn('truncado', resultado)

    def test_limite_acima_do_maximo_e_limitado(self):
        resultado = get_combustiveis(self.user_id, limite=9999)
        self.assertNotIn('erro', resultado)
        self.assertLessEqual(len(resultado['precos']), 100)


class PostosObsoletosTests(_BaseCombustiveis):
    def test_posto_com_dados_dgeg_antigos_nao_aparece(self):
        """A regra de obsolescência do módulo (30 dias) tem de se aplicar aqui."""
        obsoleto = self._criar_posto(3, 'DJB COMBUSTIVEIS', 'DJB', 'Vila Verde')
        self._criar_preco(obsoleto, 'Gasóleo simples', 1.500,
                          dgeg='2020-01-01T00:00:00.000Z')
        db.session.commit()

        resultado = get_combustiveis(self.user_id, apenas_mais_barato=True)
        nomes = [m['posto'] for m in resultado['mais_barato_por_combustivel']]
        self.assertNotIn('DJB COMBUSTIVEIS', nomes)
        self.assertEqual(resultado['mais_barato_por_combustivel'][0]['preco'], 2.113)


class FrescuraTests(_BaseCombustiveis):
    def test_recolha_acompanha_a_resposta(self):
        resultado = get_combustiveis(self.user_id)
        self.assertEqual(resultado['recolha']['ultima_atualizacao'], '2026-09-18 14:46')
        self.assertTrue(resultado['recolha']['ultima_execucao_sucesso'])

    def test_falha_na_recolha_e_reportada_ao_modelo(self):
        """Sem isto, o modelo apresentaria preços antigos como se fossem de hoje."""
        estado = EstadoAtualizacaoCombustiveis.query.get(1)
        estado.ultima_execucao_sucesso = False
        estado.mensagem_erro = 'Falhou fuel=diesel: timeout'
        db.session.commit()

        resultado = get_combustiveis(self.user_id)
        self.assertFalse(resultado['recolha']['ultima_execucao_sucesso'])
        self.assertIn('timeout', resultado['recolha']['mensagem_erro'])


class ResumoGeralTests(_BaseCombustiveis):
    def test_resumo_inclui_combustiveis_quando_ha_concelhos(self):
        resumo = executar_ferramenta('get_resumo_geral', {}, self.user_id,
                                     modo='leitura')
        self.assertEqual(resumo['combustiveis_concelhos'], ['Vila Verde'])
        self.assertEqual(resumo['combustiveis_postos_com_preco'], 1)
        self.assertEqual(resumo['combustiveis_mais_barato'][0]['preco'], 2.113)

    def test_resumo_orienta_quando_faltam_concelhos(self):
        resumo = executar_ferramenta('get_resumo_geral', {}, self.outro_user.id,
                                     modo='leitura')
        self.assertIn('combustiveis', resumo)
        self.assertIn('Definições', resumo['combustiveis'])
