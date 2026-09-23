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
MAX_CHARS_POR_MENSAGEM = 3000      # tecto por mensagem individual guardada em sessão
MAX_CHARS_HISTORICO_TOTAL = 8000   # orçamento total do histórico guardado em sessão

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
    '- Consultar tarefas, notas, jogos de Euromilhões, eventos do calendário,\n'
    '  conversões de moeda, preços de combustíveis nos concelhos do utilizador\n'
    '  e resumo geral do utilizador\n'
    '- As tuas capacidades são APENAS de leitura — não podes criar, editar ou apagar nada.\n'
    '- Quando sugerires acções ao utilizador, indica sempre que devem ser feitas '
    'directamente nos respectivos módulos (Tarefas, Notas, etc.).\n\n'
    'REGRAS\n'
    '- NUNCA inventes dados. Se não tiveres informações ou as ferramentas falharem, '
    'diz ao utilizador que não foi possível obter os dados de momento.\n'
    '- NUNCA sugiras acções que não sabes fazer (ex: "queria marcar como concluída?", '
    '"devo criar uma nova nota?"). Se o utilizador quer fazer algo, diz-lhe onde.\n'
    '- Usa as ferramentas disponíveis quando necessitares de dados concretos.\n'
    '- NUNCA inventes postos, preços ou concelhos. Os preços de combustíveis vêm da '
    'ferramenta get_combustiveis e referem-se apenas aos concelhos que o utilizador '
    'escolheu em Combustíveis → Definições; se a ferramenta devolver erro, explica o '
    'que falta e indica o módulo. Apresenta sempre o preço em €/L com 3 casas '
    'decimais e menciona a data da recolha quando for relevante.\n'
    '- Se a pergunta for simples (cumprimento, explicação, instrução), responde '
    'diretamente sem chamar ferramentas.\n'
    '- Sê conciso e directo nas respostas.\n'
    '- Mantém o tom formal e profissional.'
)

SYSTEM_PROMPT_ESCRITA = (
    'És o assistente do PIPE — uma plataforma pessoal de produtividade.\n'
    'Respostas devem ser em português europeu (pt-PT).\n\n'
    'CAPACIDADES\n'
    '- Podes consultar câmbios/conversões de moeda e preços de combustíveis nos teus\n'
    '  concelhos, além de consultar E EXECUTAR ACÇÕES nos módulos Tarefas, Notas,\n'
    '  Calendário e Passwords.\n'
    '- Sobre combustíveis tens apenas leitura: não podes mudar concelhos, combustíveis\n'
    '  de interesse nem forçar actualizações — encaminha o utilizador para o módulo\n'
    '  Combustíveis (Definições ou botão "Atualizar Dados").\n'
    '- NUNCA inventes postos, preços ou concelhos: usa a ferramenta get_combustiveis e\n'
    '  apresenta os valores em €/L com 3 casas decimais.\n'
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


LIMITE_ITENS_LISTA_TOOL = 10       # nº máximo de itens em listas dentro do resultado
LIMITE_CHARS_TOOL_RESULT = 2000    # tecto de segurança do JSON final


def _truncar_listas(valor):
    """Corta listas dentro do resultado de uma tool a LIMITE_ITENS_LISTA_TOOL itens,
    marcando 'truncado': True. Evita cortar a string JSON a meio (o que geraria
    JSON inválido) — o corte é feito na estrutura, antes de serializar."""
    if isinstance(valor, dict):
        novo = {}
        for chave, item in valor.items():
            if isinstance(item, list) and len(item) > LIMITE_ITENS_LISTA_TOOL:
                novo[chave] = item[:LIMITE_ITENS_LISTA_TOOL]
                novo['truncado'] = True
                novo.setdefault('nota', f'Mostrados {LIMITE_ITENS_LISTA_TOOL} de {len(item)} registos. Usa filtros mais específicos para ver menos de cada vez.')
            else:
                novo[chave] = _truncar_listas(item)
        return novo
    if isinstance(valor, list):
        return [_truncar_listas(v) for v in valor]
    return valor


def _serializar_resultado_tool(resultado):
    """Serializa o resultado de uma tool para o histórico, com corte por itens
    (estrutural) e um tecto final de caracteres como rede de segurança."""
    if isinstance(resultado, str):
        return resultado[:LIMITE_CHARS_TOOL_RESULT]

    resultado_cortado = _truncar_listas(resultado)
    texto = json.dumps(resultado_cortado, ensure_ascii=False)

    if len(texto) > LIMITE_CHARS_TOOL_RESULT:
        texto = json.dumps({
            'aviso': 'Resultado demasiado grande para mostrar por completo.',
            'total_aproximado': len(texto),
            'sugestao': 'Pede um filtro mais específico (ex. um concelho, uma lista, um intervalo de datas).',
        }, ensure_ascii=False)

    return texto


def _obter_historico():
    """Devolve o histórico actual de mensagens da sessão."""
    return session.get('chat_historico', [])


def _tamanho_historico(historico):
    """Soma o tamanho em caracteres do conteúdo de todas as mensagens."""
    return sum(len(m.get('content') or '') for m in historico if isinstance(m, dict))


def _limpar_historico(historico):
    """Corta o histórico para caber na sessão: por nº de mensagens, por tamanho
    de cada mensagem individual e por um orçamento total em caracteres. A
    mensagem já foi enviada ao modelo nesta chamada — este corte só afeta o
    que fica guardado para os próximos pedidos, nunca a resposta actual."""
    if len(historico) > MAX_MENSAGENS:
        historico = historico[-MAX_MENSAGENS:]

    cortado = []
    for m in historico:
        if not isinstance(m, dict):
            continue
        conteudo = m.get('content') or ''
        if len(conteudo) > MAX_CHARS_POR_MENSAGEM:
            conteudo = conteudo[:MAX_CHARS_POR_MENSAGEM] + '… (cortado no histórico guardado)'
        cortado.append({**m, 'content': conteudo})
    historico = cortado

    while len(historico) > 1 and _tamanho_historico(historico) > MAX_CHARS_HISTORICO_TOTAL:
        historico = historico[1:]

    return historico


def _guardar_historico(historico):
    """Guarda o histórico na sessão, já cortado por _limpar_historico."""
    historico = _limpar_historico(historico)
    session['chat_historico'] = historico
    session.modified = True


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
                'content': _serializar_resultado_tool(resultado),
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
