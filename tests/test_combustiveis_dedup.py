"""Testes da heurística de deduplicação de postos (módulo Combustíveis).

Um duplicado genuíno é o **mesmo posto físico** devolvido pela API Aberta com
dois `id` diferentes — o caso clássico da re-atribuição de id da DGEG, em que a
entrada antiga fica "congelada" com valores desactualizados. Nesses casos o
nome, a morada e o concelho são praticamente iguais.

A chave é deliberadamente **conservadora** — nome + morada + concelho
normalizados — para NÃO fundir estações **reais** que só partilham:
- o nome (ex.: as 4 "Santos da Cunha 6 - Logística e Transportes, Lda."
  em Braga/Vila Verde — são 4 estações distintas do mesmo operador);
- a morada (ex.: "Ilídio Mota - Palmeira 1"/"2", "Cepsa Órfãos I/II
  (Poente/Nascente)", "Repsol Piscinas I/II" — estações gémeas na mesma rua).

Usam SQLite em memória, sem tocar na BD real nem na API Aberta.
"""

from datetime import datetime, timedelta
from unittest import TestCase

from app import create_app, db
from app.combustiveis import services
from app.combustiveis.models import (
    EstadoAtualizacaoCombustiveis,
    Posto,
    PrecoHistorico,
)


def _dgeg_fresco(dias=0):
    """Timestamp DGEG fresco (dentro do MAX_DIAS_PRECO_ATIVO), formato da API."""
    return (datetime.utcnow() - timedelta(days=dias)).strftime('%Y-%m-%dT%H:%M:%S.000Z')


class _BaseDedup(TestCase):
    """App isolada com SQLite em memória e helpers de criação de postos."""

    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        estado = EstadoAtualizacaoCombustiveis.query.get(1)
        if estado is None:
            db.session.add(EstadoAtualizacaoCombustiveis(id=1))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    # ── Helpers ──────────────────────────────────────────────────────────

    def _criar_posto(self, posto_id, nome, morada, concelho, ativo=True):
        posto = Posto(id=posto_id, nome=nome, morada=morada, concelho=concelho,
                      ativo=ativo, ciclos_ausente=0)
        db.session.add(posto)
        db.session.flush()
        return posto

    def _criar_preco(self, posto, tipo, preco, dgeg=None, recolha=None):
        registo = PrecoHistorico(
            posto_id=posto.id, tipo_combustivel=tipo, preco=preco,
            data_atualizacao_dgeg=dgeg or _dgeg_fresco(),
            data_recolha=recolha or datetime.utcnow(),
        )
        db.session.add(registo)
        db.session.flush()
        return registo
class SemDuplicadosTests(_BaseDedup):
    def test_postos_distintos_nao_excluem_nada(self):
        self._criar_posto(1, 'Posto A', 'Rua A, 1', 'Braga')
        self._criar_posto(2, 'Posto B', 'Rua B, 2', 'Braga')
        db.session.commit()

        self.assertEqual(services.obter_ids_duplicados(), [])


class ChaveConservadoraTests(_BaseDedup):
    """A chave é nome + morada + concelho — cada parte isolada é irrelevante."""

    def test_mesmo_nome_mesma_morada_mesmo_concelho_e_duplicado(self):
        self._criar_posto(10, 'E.S. EXEMPLO', 'Rua Central, 5', 'Braga')
        self._criar_posto(11, 'E.S. EXEMPLO', 'Rua Central, 5', 'Braga')
        db.session.commit()

        self.assertEqual(services.obter_ids_duplicados(), [11])

    def test_mesmo_nome_moradas_diferentes_nao_e_duplicado(self):
        """Caso real: 4 "Santos da Cunha 6" em moradas diferentes."""
        self._criar_posto(20, 'Santos da Cunha 6, Lda.', 'EN 201, Merelim', 'Braga')
        self._criar_posto(21, 'Santos da Cunha 6, Lda.', 'EN 14, Av. João Paulo II', 'Braga')
        db.session.commit()

        self.assertEqual(services.obter_ids_duplicados(), [])

    def test_mesma_morada_nomes_diferentes_nao_e_duplicado(self):
        """Caso real: estações gémeas — "Palmeira 1" / "Palmeira 2"."""
        self._criar_posto(30, 'Ilídio Mota - Palmeira 1', 'Avenida Cávado 268', 'Braga')
        self._criar_posto(31, 'Ilídio Mota - Palmeira 2', 'Avenida Cávado 268', 'Braga')
        db.session.commit()

        self.assertEqual(services.obter_ids_duplicados(), [])

    def test_concelhos_diferentes_nao_e_duplicado(self):
        self._criar_posto(40, 'E.S. EXEMPLO', 'Estrada Nacional, Km 3', 'Braga')
        self._criar_posto(41, 'E.S. EXEMPLO', 'Estrada Nacional, Km 3', 'Amares')
        db.session.commit()

        self.assertEqual(services.obter_ids_duplicados(), [])

    def test_normalizacao_ignora_caixa_e_espacos(self):
        self._criar_posto(50, 'PINGO DOCE BRAGA', 'Rua A, 1', 'Braga')
        self._criar_posto(51, '  pingo  doce  braga ', ' rua a, 1 ', ' braga ')
        db.session.commit()

        self.assertEqual(services.obter_ids_duplicados(), [51])


class VencedorTests(_BaseDedup):
    """De cada grupo de duplicados fica um vencedor; os restantes são excluídos."""

    def test_vencedor_e_o_do_preco_mais_recente(self):
        vencedor = self._criar_posto(60, 'E.S. X', 'Rua X, 1', 'Braga')
        perdedor = self._criar_posto(61, 'E.S. X', 'Rua X, 1', 'Braga')
        self._criar_preco(vencedor, 'Gasóleo simples', 2.0)
        self._criar_preco(perdedor, 'Gasóleo simples', 2.5,
                          recolha=datetime.utcnow() - timedelta(days=5))
        db.session.commit()

        # O mais recente (60) fica; o mais antigo (61) é excluído.
        self.assertEqual(services.obter_ids_duplicados(), [61])

    def test_vencedor_prefere_posto_ativo(self):
        inactivo = self._criar_posto(70, 'E.S. Y', 'Rua Y, 1', 'Braga', ativo=False)
        activo = self._criar_posto(71, 'E.S. Y', 'Rua Y, 1', 'Braga', ativo=True)
        self._criar_preco(inactivo, 'Gasóleo simples', 2.0)
        self._criar_preco(activo, 'Gasóleo simples', 2.5,
                          recolha=datetime.utcnow() - timedelta(days=5))
        db.session.commit()

        # O activo (71) fica mesmo tendo o preço mais antigo.
        self.assertEqual(services.obter_ids_duplicados(), [70])

    def test_vencedor_prefere_posto_com_preco(self):
        sem_preco = self._criar_posto(80, 'E.S. Z', 'Rua Z, 1', 'Braga')
        com_preco = self._criar_posto(81, 'E.S. Z', 'Rua Z, 1', 'Braga')
        self._criar_preco(com_preco, 'Gasóleo simples', 2.0)
        db.session.commit()

        self.assertEqual(services.obter_ids_duplicados(), [80])


class LeituraTests(_BaseDedup):
    """Os duplicados não aparecem nas leituras públicas do módulo."""

    def setUp(self):
        super().setUp()
        self.vencedor = self._criar_posto(90, 'E.S. DUP', 'Rua Dup, 1', 'Braga')
        self.perdedor = self._criar_posto(91, 'E.S. DUP', 'Rua Dup, 1', 'Braga')
        # Cenário real de re-atribuição de id: o perdedor é a entrada antiga da
        # DGEG (dados 5 dias mais antigos) e marca um preço mais barato, que não
        # pode "ganhar" o card. Com 5 dias o perdedor NÃO é obsoleto (< 30), pelo
        # que o teste exercita mesmo a deduplicação, não a regra de obsolescência.
        self._criar_preco(self.vencedor, 'Gasóleo simples', 2.10)
        self._criar_preco(self.perdedor, 'Gasóleo simples', 1.50,
                          dgeg=_dgeg_fresco(5),
                          recolha=datetime.utcnow() - timedelta(days=5))
        # Um tipo que só existe no perdedor não deve figurar nas leituras.
        self._criar_preco(self.perdedor, 'Gasóleo agrícola', 1.40,
                          dgeg=_dgeg_fresco(5),
                          recolha=datetime.utcnow() - timedelta(days=5))
        db.session.commit()

    def test_precos_excluem_duplicado(self):
        resultados = services.obter_precos_para_concelhos(['Braga'])
        ids = {posto.id for posto, _ in resultados}
        self.assertIn(self.vencedor.id, ids)
        self.assertNotIn(self.perdedor.id, ids)
        precos = [preco.preco for _, preco in resultados]
        self.assertNotIn(1.50, precos)

    def test_tipos_excluem_tipo_so_do_duplicado(self):
        tipos = services.obter_tipos_combustivel_disponiveis(['Braga'])
        self.assertIn('Gasóleo simples', tipos)
        self.assertNotIn('Gasóleo agrícola', tipos)