"""Testes unitários do cliente OpenRouter (fallback e validação de resposta)."""

import os
from unittest import mock, TestCase

import requests

from app.assistente.cliente import (
    PrazoExcedidoError,
    RateLimitError,
    ServicoIndisponivelError,
    _listar_modelos,
    _classificar_resposta,
    chamar_llm,
)


class _FakeResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        if self._json_data is None:
            raise ValueError("sem corpo JSON")
        return self._json_data


def _resposta_valida():
    return _FakeResponse(200, {
        "choices": [{
            "message": {
                "content": "",
                "tool_calls": [{
                    "id": "call-1",
                    "function": {"name": "criar_evento", "arguments": "{}"},
                }],
            }
        }],
    })


def _resposta_erro_servico():
    return _FakeResponse(200, {
        "error": {"message": "upstream overload", "code": 502}
    })


MODELO_DEFAULT = "cohere/north-mini-code:free"  # hardcoded para consistência entre testes e cliente
_MODELOS_FALLBACK_BRUTOS = [
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "liquid/lfm-2.5-2.6b:free",
    "dots-studio/dots-3-note-preview:free",
    "poolside/laguna-s-2.1:free",
]
MODELOS_FALLBACK = [m for m in _MODELOS_FALLBACK_BRUTOS if m != MODELO_DEFAULT]


class ClassificacaoTests(TestCase):
    def test_200_com_corpo_de_erro_e_classificado_como_servico(self):
        cat, _ = _classificar_resposta(_resposta_erro_servico())
        self.assertEqual(cat, "servico")

    def test_429_e_rate_limit(self):
        cat, _ = _classificar_resposta(_FakeResponse(429))
        self.assertEqual(cat, "rate_limit")

    def test_404_e_modelo_indisponivel(self):
        cat, _ = _classificar_resposta(_FakeResponse(404))
        self.assertEqual(cat, "modelo_indisponivel")

    def test_500_e_servico(self):
        cat, _ = _classificar_resposta(_FakeResponse(500))
        self.assertEqual(cat, "servico")

    def test_choices_vazio_e_servico(self):
        cat, _ = _classificar_resposta(_FakeResponse(200, {"choices": []}))
        self.assertEqual(cat, "servico")

    def test_resposta_com_conteudo_e_tool_calls_e_ok(self):
        cat, _ = _classificar_resposta(_resposta_valida())
        self.assertEqual(cat, "ok")

    def test_resposta_com_conteudo_vazio_e_sem_tool_calls_e_servico(self):
        cat, _ = _classificar_resposta(_FakeResponse(200, {
            "choices": [{"message": {"content": "", "tool_calls": []}}]
        }))
        self.assertEqual(cat, "servico")


class ChamarLlmTests(TestCase):
    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch("app.assistente.cliente.time.sleep")
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_fallback_apos_429_e_erro_de_servico_ate_resposta_valida(self, _, post):
        modelos_ordenados = _listar_modelos()
        self.assertTrue(len(modelos_ordenados) >= 3, "O teste requer pelo menos 3 modelos únicos")
        m1, m2, m3 = modelos_ordenados[0], modelos_ordenados[1], modelos_ordenados[2]

        post.side_effect = [_FakeResponse(429), _resposta_erro_servico(), _resposta_valida()]

        resultado = chamar_llm([{"role": "user", "content": "cria evento"}])

        self.assertEqual(post.call_count, 3)
        self.assertEqual(post.call_args_list[0][1]["json"]["model"], m1)
        self.assertEqual(post.call_args_list[1][1]["json"]["model"], m2)
        self.assertEqual(post.call_args_list[2][1]["json"]["model"], m3)
        self.assertIn("choices", resultado)

    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch("app.assistente.cliente.time.sleep")
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_todos_os_modelos_com_rate_limit_levanta_rate_limit(self, _, post):
        modelos_ordenados = _listar_modelos()
        post.side_effect = [_FakeResponse(429) for _ in modelos_ordenados]

        with self.assertRaises(RateLimitError):
            chamar_llm([{"role": "user", "content": "cria evento"}])

        self.assertEqual(post.call_count, len(modelos_ordenados))

    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch("app.assistente.cliente.time.sleep")
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_todos_os_modelos_com_erro_de_servico_levanta_servico_indisponivel(self, _, post):
        modelos_ordenados = _listar_modelos()
        post.side_effect = [_resposta_erro_servico() for _ in modelos_ordenados]

        with self.assertRaises(ServicoIndisponivelError):
            chamar_llm([{"role": "user", "content": "cria evento"}])

        self.assertEqual(post.call_count, len(modelos_ordenados))

    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch("app.assistente.cliente.time.sleep")
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_excecao_de_rede_faz_fallback_rapidamente(self, sleep, post):
        post.side_effect = [requests.exceptions.RequestException("rede"), requests.exceptions.RequestException("rede"), _resposta_valida()]

        resultado = chamar_llm([{"role": "user", "content": "cria evento"}])

        self.assertEqual(post.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertIn("choices", resultado)

    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch.dict(os.environ, {"OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_modelo_customico_nao_listado_na_lista_fallback(self, post):
        modelos = _listar_modelos()
        self.assertIn(MODELO_DEFAULT, modelos)
        self.assertTrue(all(m in modelos for m in MODELOS_FALLBACK))
        self.assertEqual(modelos[0], MODELO_DEFAULT)

    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch.dict(os.environ, {"OPENROUTER_MODEL": MODELO_DEFAULT}, clear=True)
    def test_chave_api_em_branco_levanta_value_error(self, _):
        with self.assertRaises(ValueError):
            chamar_llm([{"role": "user", "content": "cria evento"}])


class _RelogioFalso:
    """Relógio controlável: cada consulta avança ``incremento`` segundos."""

    def __init__(self, incremento=0.0):
        self.tempo = 1000.0
        self.incremento = incremento

    def __call__(self):
        self.tempo += self.incremento
        return self.tempo


class PrazoTotalTests(TestCase):
    """Testes do parâmetro opcional ``prazo_total`` de ``chamar_llm``."""

    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_sem_prazo_mantem_timeout_de_60_segundos(self, post):
        post.return_value = _resposta_valida()

        chamar_llm([{"role": "user", "content": "cria evento"}])

        self.assertEqual(post.call_args.kwargs["timeout"], 60)

    @mock.patch("app.assistente.cliente.time.monotonic", _RelogioFalso())
    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_prazo_limita_timeout_do_pedido_ao_tempo_restante(self, post):
        post.return_value = _resposta_valida()

        chamar_llm([{"role": "user", "content": "cria evento"}], prazo_total=7)

        self.assertEqual(post.call_args.kwargs["timeout"], 7)

    @mock.patch("app.assistente.cliente.time.monotonic", _RelogioFalso(incremento=5))
    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_prazo_excedido_entre_modelos_para_antes_do_segundo(self, post):
        # A resposta de erro consome tempo; o 2.º modelo já não é chamado.
        post.side_effect = [_resposta_erro_servico()]

        with self.assertRaises(PrazoExcedidoError):
            chamar_llm([{"role": "user", "content": "cria evento"}], prazo_total=8)

        self.assertEqual(post.call_count, 1)

    @mock.patch("app.assistente.cliente.time.monotonic", _RelogioFalso(incremento=1))
    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_prazo_excedido_antes_do_primeiro_pedido(self, post):
        with self.assertRaises(PrazoExcedidoError):
            chamar_llm([{"role": "user", "content": "cria evento"}], prazo_total=0.5)

        post.assert_not_called()

    @mock.patch("app.assistente.cliente.time.sleep")
    @mock.patch("app.assistente.cliente.time.monotonic", _RelogioFalso(incremento=2))
    @mock.patch("app.assistente.cliente.requests.post")
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENROUTER_MODEL": MODELO_DEFAULT})
    def test_prazo_corta_backoff_de_rede(self, post, sleep):
        post.side_effect = requests.exceptions.RequestException("rede")

        with self.assertRaises(PrazoExcedidoError):
            chamar_llm([{"role": "user", "content": "cria evento"}], prazo_total=5)

        # O backoff de 2s não cabe no ~1s restante: falha sem dormir.
        sleep.assert_not_called()

