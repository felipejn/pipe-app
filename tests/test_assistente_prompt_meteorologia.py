"""Invariante anti-alucinacao do prompt de meteorologia do Assistente IA.

Garante que nunca mais acontece o incidente de 08/10/2026, em que o modelo
respondeu com tabelas de temperaturas inventadas (minimas 15->9 C, maximas
23->19 C) sem chamar `get_meteorologia`, inventou ainda um falso limite
("previsao apenas ate 14/10 - limite da ferramenta") e so corrigiu apos o
utilizador confrontar ("onde obteve estes dados? ou voce inventou?").

Os testes sao puras assercoes sobre strings (sem BD, sem HTTP): verificam
que ambos os system prompts obrigam a chamada previa a ferramenta, proibe
apresentar valores sem resultado da ferramenta, exigem citar fonte +
data de actualizacao e explicam o horizonte de 7 dias rolantes.
"""

from unittest import TestCase

from app.assistente.contexto import (
    SYSTEM_PROMPT_ESCRITA,
    SYSTEM_PROMPT_LEITURA,
)
from app.assistente.ferramentas import DEFINICOES_FERRAMENTAS_LEITURA


def _descricao_meteorologia():
    for bloco in DEFINICOES_FERRAMENTAS_LEITURA:
        funcao = bloco.get('function') or {}
        if funcao.get('name') == 'get_meteorologia':
            return funcao.get('description') or ''
    return ''


class PromptMeteorologiaTests(TestCase):
    """Ambos os modos tem de conter as tres clausulas anti-alucinacao."""

    PROMPTS = (SYSTEM_PROMPT_LEITURA, SYSTEM_PROMPT_ESCRITA)

    def test_obriga_chamada_previa_a_ferramenta(self):
        for prompt in self.PROMPTS:
            with self.subTest(modo='leitura' if prompt is SYSTEM_PROMPT_LEITURA else 'escrita'):
                self.assertIn('get_meteorologia', prompt)
                self.assertIn('obriga', prompt.lower())

    def test_proibe_valores_sem_resultado_da_ferramenta(self):
        for prompt in self.PROMPTS:
            with self.subTest(modo='leitura' if prompt is SYSTEM_PROMPT_LEITURA else 'escrita'):
                minusculas = prompt.lower()
                self.assertIn('nunca', minusculas)
                self.assertIn('sem um resultado da ferramenta', minusculas)

    def test_exige_citar_fonte_e_data_de_actualizacao(self):
        for prompt in self.PROMPTS:
            with self.subTest(modo='leitura' if prompt is SYSTEM_PROMPT_LEITURA else 'escrita'):
                self.assertIn('Open-Meteo', prompt)
                self.assertIn('meta.atualizada_em', prompt)

    def test_explica_horizonte_rolante_sem_limite_fixo(self):
        for prompt in self.PROMPTS:
            with self.subTest(modo='leitura' if prompt is SYSTEM_PROMPT_LEITURA else 'escrita'):
                minusculas = prompt.lower()
                self.assertIn('7 dias rolantes', minusculas)
                self.assertIn('nunca inventes um limite fixo', minusculas)

    def test_pergunta_simples_nao_dispensa_ferramenta_do_tempo(self):
        self.assertIn('excepto perguntas sobre tempo', SYSTEM_PROMPT_LEITURA.lower())

    def test_descricao_da_ferramenta_manda_chamar_antes_de_responder(self):
        descricao = _descricao_meteorologia()
        self.assertTrue(descricao, 'get_meteorologia sem descricao anunciada')
        minusculas = descricao.lower()
        self.assertIn('obrigat', minusculas)
        self.assertIn('nunca estimar', minusculas)
