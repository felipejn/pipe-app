"""Orquestração do Assistente PIPE.

Gere o histórico em sessão (limite de 20 mensagens = 10 trocas) e
orquestra o fluxo de chamadas à API OpenRouter com tool use.
"""

import json
import time
import traceback
from datetime import datetime

from flask import session

from app.assistente.cliente import (
    RateLimitError,
    ServicoIndisponivelError,
    chamar_llm,
)
from app.assistente.ferramentas import (
    DEFINICOES_FERRAMENTAS_LEITURA,
    DEFINICOES_FERRAMENTAS_ESCRITA,
    executar_ferramenta,
)

# Limite de mensagens no histórico — 10 trocas (utilizador + assistente)
MAX_MENSAGENS = 20
MAX_TOOL_ITERATIONS = 4

# Nomes dos dias da semana em português europeu. Não usamos strftime('%A')
# porque depende da locale do sistema e devolveria inglês por omissão.
_DIAS_SEMANA = (
    'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira',
    'sexta-feira', 'sábado', 'domingo',
)


def _contexto_temporal():
    """Devolve a data e a hora actuais em pt-PT, para anexar ao system prompt.

    É calculado a cada pedido (e não uma vez no import do módulo) para não
    ficar desactualizado quando a aplicação fica dias em execução. Sem esta
    referência, o modelo não consegue resolver expressões relativas
    ("hoje", "amanhã", "na próxima sexta") e acabaria por inventar datas,
    uma vez que as ferramentas de escrita exigem ISO 8601 absoluto.
    """
    agora = datetime.now()
    dia_semana = _DIAS_SEMANA[agora.weekday()]
    return (
        '\n\nDATA E HORA ACTUAIS\n'
        f'- Hoje é {dia_semana}, {agora.strftime("%d/%m/%Y")} '
        f'(formato ISO: {agora.strftime("%Y-%m-%d")}).\n'
        f'- Hora actual: {agora.strftime("%H:%M")}.\n'
        '- Usa esta referência para converter expressões relativas em datas '
        'ISO 8601 absolutas antes de chamares as ferramentas.\n'
    )


SYSTEM_PROMPT_LEITURA = (
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

SYSTEM_PROMPT_ESCRITA = (
    'És o assistente do PIPE — uma plataforma pessoal de produtividade.\n'
    'Respostas devem ser em português europeu (pt-PT).\n\n'
    'CAPACIDADES\n'
    '- Podes consultar E EXECUTAR ACÇÕES nos módulos Tarefas, Notas, Calendário e Passwords.\n'
    '- Antes de apagar qualquer coisa (tarefa, nota, evento), chama primeiro a ferramenta '
    'sem confirmado=true. Se ela devolver confirmacao_necessaria, PERGUNTA ao utilizador '
    'em texto e só voltas a chamar com confirmado=true depois de ele confirmar '
    'explicitamente. Nunca assumas confirmação.\n'
    '- Nunca inventes IDs de tarefas, notas ou eventos — usa sempre os IDs devolvidos '
    'pelas ferramentas de consulta.\n\n'
    'REGRAS\n'
    '- NUNCA inventes dados. Se uma ferramenta falhar ou devolver erro, informa o '
    'utilizador em vez de simular sucesso.\n'
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


def processar_mensagem_assistente(mensagem_utilizador, user_id, historico=None, modo=None):
    """Processa uma mensagem do utilizador através do Assistente PIPE.

    Quando chamada em contexto de requisição (Flask session), passa None
    como historico. Para testes offline, passa uma lista externa mutável.

    Fluxo:
      1. monta system prompt + histórico + nova mensagem
      2. entra num ciclo de tool use (máx. MAX_TOOL_ITERATIONS), chamando
         sempre o LLM com as definições de ferramentas
      3. se o modelo pediu tool call — executa e volta a chamar o modelo
      4. se o modelo respondeu directamente — devolve a resposta tal como veio
      5. guarda histórico actualizado

    Args:
        mensagem_utilizador: texto do utilizador.
        user_id: ID do utilizador autenticado (injetado pelo caller).
        historico: lista externa de mensagens (opcional; usa Flask session se None).
        modo: 'leitura' ou 'escrita' (opcional; lê da sessão se None e usando sessão).

    Returns:
        Se historico é lista: (resposta_str, historico_actualizado)
        Se historico é None: apenas resposta_str (usa Flask session internamente).
    """
    usar_sessao = historico is None
    if usar_sessao:
        historico = _obter_historico()
        modo = session.get('assistente_modo', 'leitura')
    elif modo is None:
        modo = 'leitura'

    system_prompt = SYSTEM_PROMPT_ESCRITA if modo == 'escrita' else SYSTEM_PROMPT_LEITURA
    # Anexa a data/hora actuais a cada pedido, para o modelo resolver
    # expressões relativas ("amanhã", "na próxima sexta") sem inventar datas.
    system_prompt += _contexto_temporal()
    ferramentas = DEFINICOES_FERRAMENTAS_ESCRITA if modo == 'escrita' else DEFINICOES_FERRAMENTAS_LEITURA

    # Adiciona a mensagem do utilizador ao histórico
    historico.append({'role': 'user', 'content': mensagem_utilizador})

    # Monta a lista de mensagens para a API
    mensagens = [{'role': 'system', 'content': system_prompt}] + historico

    def _finalizar_erro(msg):
        """Regista a mensagem de erro no histórico e devolve no formato correcto."""
        historico.append({'role': 'assistant', 'content': msg})
        hist = _limpar_historico(historico)
        if usar_sessao:
            _guardar_historico(hist)
            return msg, None
        return msg, hist, None

    resposta_texto = None
    modelo = None

    def _registar_resposta_invalida(resposta):
        """Regista uma amostra da escolha recebida quando não há resposta útil."""
        escolha = {}
        if isinstance(resposta, dict):
            escolhas = resposta.get('choices')
            if isinstance(escolhas, list) and escolhas:
                escolha = escolhas[0] if isinstance(escolhas[0], dict) else escolhas[0]
        try:
            resumo = json.dumps(escolha, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            resumo = repr(escolha)
        if len(resumo) > 1000:
            resumo = resumo[:1000] + '...'
        print(f'[Assistente RESPOSTA INVALIDA] escolha={resumo}')

    # ── Ciclo de tool use com limite de iterações ─────────────────────────
    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            resposta = chamar_llm(mensagens, ferramentas=ferramentas)
        except RateLimitError:
            return _finalizar_erro('O assistente atingiu o limite de pedidos. Aguarda um momento e tenta novamente.')
        except ServicoIndisponivelError:
            return _finalizar_erro('O serviço de IA está temporariamente indisponível. Aguarda um momento e tenta novamente.')
        except Exception as e:
            traceback.print_exc()
            print(f'[Assistente ERRO] {type(e).__name__}: {e}')
            return _finalizar_erro('Neste momento não conseguimos processar o teu pedido. Tenta novamente mais tarde.')

        modelo = resposta.get('model', 'desconhecido') if isinstance(resposta, dict) else 'desconhecido'
        escolhas = resposta.get('choices') if isinstance(resposta, dict) else None
        escolha = escolhas[0] if isinstance(escolhas, list) and escolhas else {}
        if not isinstance(escolha, dict):
            escolha = {}
        mensagem = escolha.get('message')
        if not isinstance(mensagem, dict):
            mensagem = {}
        tool_calls = mensagem.get('tool_calls')
        if not isinstance(tool_calls, list):
            tool_calls = []

        if not tool_calls:
            conteudo = mensagem.get('content')
            if not isinstance(conteudo, str) or not conteudo.strip():
                _registar_resposta_invalida(resposta)
                resposta_texto = 'Não consegui gerar uma resposta. Tenta reformular a tua pergunta.'
            else:
                resposta_texto = conteudo
            break

        # Constrói a mensagem de assistant com os tool_calls
        mensagens.append({
            'role': 'assistant',
            'content': mensagem.get('content') or '',
            'tool_calls': tool_calls,
        })

        # Executa cada tool_call e recolhe os resultados
        for tc in tool_calls:
            if not isinstance(tc, dict):
                return _finalizar_erro('Recebi uma chamada de ferramenta inválida. Tenta reformular o pedido.')
            funcao = tc.get('function')
            if not isinstance(funcao, dict):
                return _finalizar_erro('Recebi uma chamada de ferramenta inválida. Tenta reformular o pedido.')
            nome_ferramenta = funcao.get('name')
            if not isinstance(nome_ferramenta, str) or not nome_ferramenta:
                return _finalizar_erro('Recebi uma chamada de ferramenta inválida. Tenta reformular o pedido.')
            if not isinstance(tc.get('id'), str) or not tc['id']:
                return _finalizar_erro('Recebi uma chamada de ferramenta inválida. Tenta reformular o pedido.')

            argumentos_raw = funcao.get('arguments', {})
            if isinstance(argumentos_raw, str):
                try:
                    argumentos = json.loads(argumentos_raw)
                except (json.JSONDecodeError, TypeError):
                    argumentos = {}
            elif isinstance(argumentos_raw, dict):
                argumentos = argumentos_raw
            else:
                argumentos = {}

            try:
                resultado = executar_ferramenta(nome_ferramenta, argumentos, user_id, modo=modo)
            except Exception as e:
                traceback.print_exc()
                print(f'[Assistente FERRAMENTA ERRO] {nome_ferramenta}: {type(e).__name__}: {e}')
                resultado = {'erro': 'Não foi possível executar a operação pedida.'}

            mensagens.append({
                'role': 'tool',
                'tool_call_id': tc['id'],
                'content': json.dumps(resultado, ensure_ascii=False) if not isinstance(resultado, str) else resultado,
            })

        time.sleep(2)
    else:
        resposta_texto = 'Consegui obter os dados, mas o pedido tornou-se demasiado complexo. Podes reformular de forma mais simples?'

    # Atualiza histórico com a resposta do assistente
    historico.append({'role': 'assistant', 'content': resposta_texto})
    historico = _limpar_historico(historico)

    if usar_sessao:
        _guardar_historico(historico)
        return resposta_texto, modelo

    return resposta_texto, historico, modelo
