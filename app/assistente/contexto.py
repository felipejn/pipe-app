"""Orquestração do Assistente PIPE.

Gere o histórico em sessão (limite de 20 mensagens = 10 trocas) e
orquestra o fluxo de chamadas à API OpenRouter com tool use.
"""

import json
import time

from flask import session

from app.assistente.cliente import RateLimitError, chamar_llm
from app.assistente.ferramentas import DEFINICOES_FERRAMENTAS, executar_ferramenta

# Limite de mensagens no histórico — 10 trocas (utilizador + assistente)
MAX_MENSAGENS = 20

SYSTEM_PROMPT = (
    'És o assistente do PIPE — uma plataforma pessoal de produtividade.\n'
    'Respostas devem ser em português europeu (pt-PT).\n\n'
    'CAPACIDADES\n'
    '- Consultar tarefas, notas, jogos de Euromilhões e resumo geral do utilizador\n'
    '- As tuas capacidades são APENAS de leitura — não podes criar, editar ou apagar nada.\n'
    '- Quando sugerires acções ao utilizador, indica sempre que devem ser feitas '
    'directamente nos respectivos módulos (Tarefas, Notas, etc.).\n\n'
    'REGRAS\n'
    '- NUNCA inventes dados. Se não tiveres informações ou as ferramentas falharem, '
    'diz ao utilizador que não foi possível obter os dados de momento.\n'
    '- NUNCA sugiras acções que não sabes fazer (ex: "queria marcar como concluída?", '
    '"devo criar uma nova nota?"). Se o utilizador quer fazer algo, diz-lhe onde.\n'
    '- Usa as ferramentas disponíveis quando necessitares de dados concretos.\n'
    '- Se a pergunta for simples (cumprimento, explicação, instrução), responde '
    'diretamente sem chamar ferramentas.\n'
    '- Sê conciso e directo nas respostas.\n'
    '- Mantém o tom formal e profissional.'
)


def _obter_historico():
    """Devolve o histórico actual de mensagens da sessão."""
    return session.get('chat_historico', [])


def _guardar_historico(historico):
    """Guarda o histórico na sessão, respeitando o limite de 20 mensagens."""
    # Se excedeu o limite, remove as mais antigas (mantém as mais recentes)
    if len(historico) > MAX_MENSAGENS:
        historico = historico[-MAX_MENSAGENS:]
    session['chat_historico'] = historico
    session.modified = True


def _limpar_historico(historico):
    """Trunca o histórico se exceder o limite."""
    if len(historico) > MAX_MENSAGENS:
        return historico[-MAX_MENSAGENS:]
    return historico


def processar_mensagem_assistente(mensagem_utilizador, user_id, historico=None):
    """Processa uma mensagem do utilizador através do Assistente PIPE.

    Quando chamada em contexto de requisição (Flask session), passa None
    como historico. Para testes offline, passa uma lista externa mutável.

    Fluxo:
      1. monta system prompt + histórico + nova mensagem
      2. chama OpenRouter com definições de ferramentas
      3. se o modelo pediu tool call — executa a ferramenta e faz segunda chamada
      4. se o modelo respondeu directamente — devolve a resposta tal como veio
      5. guarda histórico actualizado

    Args:
        mensagem_utilizador: texto do utilizador.
        user_id: ID do utilizador autenticado (injetado pelo caller).
        historico: lista externa de mensagens (opcional; usa Flask session se None).

    Returns:
        Se historico é lista: (resposta_str, historico_actualizado)
        Se historico é None: apenas resposta_str (usa Flask session internamente).
    """
    usar_sessao = historico is None
    if usar_sessao:
        historico = _obter_historico()

    # Adiciona a mensagem do utilizador ao histórico
    historico.append({'role': 'user', 'content': mensagem_utilizador})

    # Monta a lista de mensagens para a API
    mensagens = [{'role': 'system', 'content': SYSTEM_PROMPT}] + historico

    # ── Primeira chamada ao modelo ────────────────────────────────────────
    try:
        resposta = chamar_llm(mensagens, ferramentas=DEFINICOES_FERRAMENTAS)
    except RateLimitError:
        erro_msg = 'O assistente atingiu o limite de pedidos. Aguarda um momento e tenta novamente.'
        historico.append({'role': 'assistant', 'content': erro_msg})
        historico = _limpar_historico(historico)
        if usar_sessao:
            _guardar_historico(historico)
            return erro_msg
        return erro_msg, historico
    except Exception:
        erro_msg = 'Neste momento não consegui processar o teu pedido. Tenta novamente mais tarde.'
        historico.append({'role': 'assistant', 'content': erro_msg})
        historico = _limpar_historico(historico)
        if usar_sessao:
            _guardar_historico(historico)
            return erro_msg
        return erro_msg, historico

    escolha = resposta.get('choices', [{}])[0].get('message', {})

    # ── Caso 1: modelo chamou ferramenta(s) ───────────────────────────────
    tool_calls = escolha.get('tool_calls')
    if tool_calls:
        # Constrói a mensagem de assistant com os tool_calls para o histórico
        msg_assistente = {
            'role': 'assistant',
            'content': escolha.get('content'),
            'tool_calls': tool_calls,
        }

        # Executa cada tool_call e recolhe os resultados
        mensagens.append(msg_assistente)
        for tc in tool_calls:
            nome_ferramenta = tc['function']['name']
            argumentos = json.loads(tc['function']['arguments'])

            resultado = executar_ferramenta(nome_ferramenta, argumentos, user_id)

            mensagens.append({
                'role': 'tool',
                'tool_call_id': tc['id'],
                'content': json.dumps(resultado, ensure_ascii=False) if not isinstance(resultado, str) else resultado,
            })

        # Segunda chamada ao modelo com os dados da ferramenta
        time.sleep(2)
        try:
            resposta_final = chamar_llm(mensagens)
        except RateLimitError:
            erro_msg = 'O assistente atingiu o limite de pedidos. Aguarda um momento e tenta novamente.'
            historico.append({'role': 'assistant', 'content': erro_msg})
            historico = _limpar_historico(historico)
            if usar_sessao:
                _guardar_historico(historico)
                return erro_msg
            return erro_msg, historico
        except Exception:
            import traceback
            traceback.print_exc()
            erro_msg = 'Recebi os dados da consulta, mas não consegui formular a resposta. Tenta novamente.'
            historico.append({'role': 'assistant', 'content': erro_msg})
            historico = _limpar_historico(historico)
            if usar_sessao:
                _guardar_historico(historico)
                return erro_msg
            return erro_msg, historico

        resposta_texto = resposta_final.get('choices', [{}])[0].get('message', {}).get('content', '')

    # ── Caso 2: modelo respondeu directamente (sem tool use) ──────────────
    else:
        resposta_texto = escolha.get('content', 'Não consegui gerar uma resposta. Tenta reformular a tua pergunta.')

    # Atualiza histórico com a resposta do assistente
    historico.append({'role': 'assistant', 'content': resposta_texto})
    historico = _limpar_historico(historico)

    if usar_sessao:
        _guardar_historico(historico)
        return resposta_texto

    return resposta_texto, historico
