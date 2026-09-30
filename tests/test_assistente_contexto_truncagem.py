"""Testes do corte dos resultados de ferramentas enviados ao modelo.

Contexto (bug observado): `_serializar_resultado_tool()` aplicava o corte
estrutural de listas a 10 itens e, se o JSON continuasse acima de
`LIMITE_CHARS_TOOL_RESULT`, substituía o resultado **inteiro** por um aviso — o
modelo ficava sem dados nenhuns naquele pedido. Aconteceu com
`get_combustiveis`: os 14 registos de um concelho davam 2 853 chars e o
assistente recebia o aviso em vez dos preços, não conseguindo responder a
"quanto está o gasóleo simples no Pingo Doce de Vila Verde?".

A correcção encolhe as listas progressivamente (LIMITES_ITENS_DEGRADACAO) até o
JSON caber, deixando o aviso apenas como último recurso.
"""

import json
from unittest import TestCase

from app.assistente.contexto import (
    LIMITE_CHARS_TOOL_RESULT,
    LIMITE_ITENS_LISTA_TOOL,
    LIMITES_ITENS_DEGRADACAO,
    _serializar_resultado_tool,
    _truncar_listas,
)


def _registo(i, tamanho_extra=0):
    """Registo no formato actual (enxuto) de get_combustiveis."""
    return {
        'posto': f'POSTO {i:02d} DE VILA VERDE' + 'X' * tamanho_extra,
        'marca': 'PINGO DOCE',
        'concelho': 'Vila Verde',
        'tipo_combustivel': 'Gasóleo simples',
        'preco': 2.129,
        'data_dgeg': '2026-09-30T06:30:24.946Z',
    }


def _payload_enxuto(n):
    """Payload que cabe a 10 itens dentro do tecto de caracteres."""
    return {'precos': [_registo(i) for i in range(n)]}


def _payload_volumoso(n, tamanho_extra=0):
    """Registos com os campos que a ferramenta devolvia antes da correcção
    ('morada' + 'data_recolha'): é este volume que fazia o JSON de um concelho
    exceder LIMITE_CHARS_TOOL_RESULT e chegava ao modelo como um aviso."""
    return {
        'precos': [
            dict(_registo(i, tamanho_extra),
                 morada='Rua Exemplo, 123, Vila Verde',
                 data_recolha='2026-09-30 22:06')
            for i in range(n)
        ],
    }


class PayloadQueCabeTests(TestCase):
    def test_payload_pequeno_passa_intacto(self):
        payload = _payload_enxuto(3)
        dados = json.loads(_serializar_resultado_tool(payload))
        self.assertEqual(dados, payload)
        self.assertNotIn('truncado', dados)

    def test_lista_acima_do_limite_de_itens_e_cortada_e_assinalada(self):
        total = LIMITE_ITENS_LISTA_TOOL + 5
        dados = json.loads(_serializar_resultado_tool(_payload_enxuto(total)))
        self.assertEqual(len(dados['precos']), LIMITE_ITENS_LISTA_TOOL)
        self.assertTrue(dados['truncado'])
        self.assertIn(f'{LIMITE_ITENS_LISTA_TOOL} de {total}', dados['nota'])

    def test_string_e_cortada_ao_tecto(self):
        texto = _serializar_resultado_tool('a' * (LIMITE_CHARS_TOOL_RESULT + 500))
        self.assertEqual(len(texto), LIMITE_CHARS_TOOL_RESULT)


class RegressaoCombustiveisTests(TestCase):
    """O caso real: 14 registos de um concelho não cabiam e o modelo ficava sem dados."""

    def test_registos_chegam_ao_modelo_mesmo_acima_do_tecto(self):
        texto = _serializar_resultado_tool(_payload_volumoso(14))
        self.assertLessEqual(len(texto), LIMITE_CHARS_TOOL_RESULT)
        dados = json.loads(texto)  # tem de ser JSON válido
        self.assertNotIn('aviso', dados)
        self.assertTrue(dados['precos'], 'o modelo tem de receber registos, não só um aviso')
        self.assertTrue(dados['truncado'])
        self.assertLess(len(dados['precos']), 14)

    def test_um_unico_registo_maior_que_o_tecto_cai_no_aviso(self):
        """Não há forma de entregar: a degradação chega a 1 item e ainda não cabe."""
        payload = _payload_volumoso(1, tamanho_extra=LIMITE_CHARS_TOOL_RESULT)
        dados = json.loads(_serializar_resultado_tool(payload))
        self.assertIn('aviso', dados)
        self.assertIn('total_aproximado', dados)
        self.assertIn('sugestao', dados)

    def test_ordem_de_degradacao_e_decrescente_ate_um(self):
        self.assertEqual(LIMITES_ITENS_DEGRADACAO[0], LIMITE_ITENS_LISTA_TOOL)
        self.assertEqual(list(LIMITES_ITENS_DEGRADACAO),
                         sorted(LIMITES_ITENS_DEGRADACAO, reverse=True))
        self.assertEqual(LIMITES_ITENS_DEGRADACAO[-1], 1)


class TruncarListasTests(TestCase):
    def test_limite_personalizado(self):
        dados = _truncar_listas({'itens': list(range(10))}, 4)
        self.assertEqual(dados['itens'], [0, 1, 2, 3])
        self.assertTrue(dados['truncado'])

    def test_lista_no_limite_nao_e_marcada(self):
        dados = _truncar_listas({'itens': list(range(4))}, 4)
        self.assertEqual(dados, {'itens': [0, 1, 2, 3]})

    def test_listas_aninhadas(self):
        dados = _truncar_listas({'nivel': {'itens': list(range(6))}}, 2)
        self.assertEqual(dados['nivel']['itens'], [0, 1])
        self.assertTrue(dados['nivel']['truncado'])

    def test_valores_escalares_intactos(self):
        self.assertEqual(_truncar_listas({'a': 1, 'b': 'x'}, 2), {'a': 1, 'b': 'x'})
