"""Testes unitários da orquestração do assistente (parsing de respostas e fluxo)."""

import json
from unittest import mock, TestCase

from app.assistente.cliente import RateLimitError, ServicoIndisponivelError
from app.assistente.contexto import processar_mensagem_assistente


def _resposta(conteudo=None, tool_calls=None):
    mensagem = {}
    if conteudo is not None:
        mensagem["content"] = conteudo
    if tool_calls is not None:
        mensagem["tool_calls"] = tool_calls
    return {"choices": [{"message": mensagem}]}


def _tool_call(nome="criar_evento", arguments=None, call_id="call-1"):
    return {
        "id": call_id,
        "function": {"name": nome, "arguments": arguments or "{}"},
    }


class ProcessarMensagemTests(TestCase):
    @mock.patch("app.assistente.contexto.chamar_llm")
    @mock.patch("app.assistente.contexto.executar_ferramenta")
    @mock.patch("app.assistente.contexto.time.sleep")
    def test_resposta_vazia_sem_tool_calls_retorna_mensagem_amigavel(
        self, sleep, executar, chamar_llm
    ):
        chamar_llm.return_value = {"choices": []}

        resultado, historico, modelo = processar_mensagem_assistente(
            "cria um evento", user_id=1, historico=[], modo="escrita"
        )

        self.assertEqual(
            resultado,
            "Não consegui gerar uma resposta. Tenta reformular a tua pergunta.",
        )
        self.assertEqual(modelo, 'desconhecido')
        self.assertEqual(len(historico), 2)
        self.assertEqual(historico[0]["role"], "user")
        self.assertEqual(historico[1]["role"], "assistant")

    @mock.patch("app.assistente.contexto.chamar_llm")
    @mock.patch("app.assistente.contexto.executar_ferramenta")
    @mock.patch("app.assistente.contexto.time.sleep")
    def test_conteudo_valido_sem_tool_calls_retorna_conteudo(self, sleep, executar, chamar_llm):
        chamar_llm.return_value = _resposta(conteudo="Olá, posso ajudar.")

        resultado, _, _ = processar_mensagem_assistente(
            "olá", user_id=1, historico=[], modo="leitura"
        )

        self.assertEqual(resultado, "Olá, posso ajudar.")

    @mock.patch("app.assistente.contexto.chamar_llm")
    @mock.patch("app.assistente.contexto.executar_ferramenta")
    @mock.patch("app.assistente.contexto.time.sleep")
    def test_modelo_devolvido_da_resposta_api(self, sleep, executar, chamar_llm):
        chamar_llm.return_value = {"model": "thinkingmachines/inkling-small:free", "choices": [{"message": {"content": "Olá!"}}]}

        resultado, _, modelo = processar_mensagem_assistente(
            "olá", user_id=1, historico=[], modo="leitura"
        )

        self.assertEqual(resultado, "Olá!")
        self.assertEqual(modelo, "thinkingmachines/inkling-small:free")

    @mock.patch("app.assistente.contexto.chamar_llm")
    @mock.patch("app.assistente.contexto.executar_ferramenta")
    @mock.patch("app.assistente.contexto.time.sleep")
    def test_tool_call_executa_e_retorna_resposta_final(
        self, sleep, executar, chamar_llm
    ):
        chamar_llm.side_effect = [
            _resposta(tool_calls=[_tool_call()]),
            _resposta(conteudo="Evento criado."),
        ]
        executar.return_value = {"ok": True}

        resultado, _, _ = processar_mensagem_assistente(
            "cria evento", user_id=1, historico=[], modo="escrita"
        )

        self.assertEqual(resultado, "Evento criado.")
        executar.assert_called_once_with(
            "criar_evento", {}, 1, modo="escrita"
        )
        self.assertEqual(sleep.call_count, 1)

    @mock.patch("app.assistente.contexto.chamar_llm")
    @mock.patch("app.assistente.contexto.executar_ferramenta")
    @mock.patch("app.assistente.contexto.time.sleep")
    def test_falha_da_ferramenta_e_tratada_sem_excecao(
        self, sleep, executar, chamar_llm
    ):
        chamar_llm.side_effect = [
            _resposta(tool_calls=[_tool_call()]),
            _resposta(conteudo="Tente novamente."),
        ]
        executar.side_effect = RuntimeError("base de dados inacessível")

        resultado, _, _ = processar_mensagem_assistente(
            "cria evento", user_id=1, historico=[], modo="escrita"
        )

        self.assertEqual(resultado, "Tente novamente.")

    @mock.patch("app.assistente.contexto.chamar_llm")
    @mock.patch("app.assistente.contexto.executar_ferramenta")
    @mock.patch("app.assistente.contexto.time.sleep")
    def test_servico_indisponivel_retorna_mensagem_amigavel(
        self, sleep, executar, chamar_llm
    ):
        chamar_llm.side_effect = ServicoIndisponivelError("sobrecarga")

        resultado, _, _ = processar_mensagem_assistente(
            "cria evento", user_id=1, historico=[], modo="escrita"
        )

        self.assertIn(
            "serviço de IA está temporariamente indisponível", resultado
        )

    @mock.patch("app.assistente.contexto.chamar_llm")
    @mock.patch("app.assistente.contexto.executar_ferramenta")
    @mock.patch("app.assistente.contexto.time.sleep")
    def test_rate_limit_retorna_mensagem_amigavel(self, sleep, executar, chamar_llm):
        chamar_llm.side_effect = RateLimitError("limite")

        resultado, _, _ = processar_mensagem_assistente(
            "cria evento", user_id=1, historico=[], modo="escrita"
        )

        self.assertIn("limite de pedidos", resultado)

    @mock.patch("app.assistente.contexto.chamar_llm")
    @mock.patch("app.assistente.contexto.executar_ferramenta")
    @mock.patch("app.assistente.contexto.time.sleep")
    def test_chamada_de_ferramenta_invalida_retorna_mensagem(self, sleep, executar, chamar_llm):
        chamar_llm.return_value = _resposta(
            tool_calls=[{"function": {"name": "criar_evento", "arguments": "{}"}}]
        )

        resultado, _, _ = processar_mensagem_assistente(
            "cria evento", user_id=1, historico=[], modo="escrita"
        )

        self.assertIn("chamada de ferramenta inválida", resultado)

    @mock.patch("app.assistente.contexto.chamar_llm")
    @mock.patch("app.assistente.contexto.executar_ferramenta")
    @mock.patch("app.assistente.contexto.time.sleep")
    def test_argumentos_dentro_de_dict_sao_passados_corretamente(
        self, sleep, executar, chamar_llm
    ):
        args = {"titulo": "Cortar cabelo", "data_inicio": "2026-09-17T09:00:00"}
        chamar_llm.side_effect = [
            _resposta(tool_calls=[_tool_call(arguments=json.dumps(args))]),
            _resposta(conteudo="Agendado."),
        ]
        executar.return_value = {"ok": True}

        resultado, _, _ = processar_mensagem_assistente(
            "cria evento", user_id=1, historico=[], modo="escrita"
        )

        self.assertEqual(resultado, "Agendado.")
        executar.assert_called_once_with(
            "criar_evento", args, 1, modo="escrita"
        )

