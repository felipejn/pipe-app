"""Cliente HTTP para a API OpenRouter com retry e fallback entre modelos gratuitos."""

import json
import os
import time

import requests

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

_MAX_TENTATIVAS = 3
_ESPERA_RETRY = [2, 5, 10]  # segundos de backoff entre tentativas
_MODELOS_FALLBACK = [
    'nvidia/nemotron-3-super-120b-a12b:free',
    'liquid/lfm-2.5-2.6b:free',
    'dots-studio/dots-3-note-preview:free',
    'poolside/laguna-s-2.1:free',
]


class RateLimitError(Exception):
    """Erro quando todos os modelos gratuitos estao com rate limit excedido."""


class ServicoIndisponivelError(Exception):
    """Erro quando nenhum modelo conseguiu processar o pedido."""


class PrazoExcedidoError(Exception):
    """Erro quando o prazo total indicado expira antes de haver resposta."""


class ContextoExcedidoError(Exception):
    """Todos os modelos disponíveis rejeitaram o tamanho do contexto."""


def _listar_modelos():
    """Devolve lista de modelos gratuitos disponiveis, ordenados por preferencia."""
    padrao = os.environ.get('OPENROUTER_MODEL') or 'cohere/north-mini-code:free'
    modelos = [padrao]
    for modelo in _MODELOS_FALLBACK:
        if modelo != padrao and modelo not in modelos:
            modelos.append(modelo)
    return modelos


def _detalhes_erro(dados):
    """Extrai uma mensagem curta e nao sensivel de um erro da API."""
    erro = dados.get('error') if isinstance(dados, dict) else None
    if isinstance(erro, dict):
        mensagem = (
            erro.get('message')
            or erro.get('raw')
            or erro.get('code')
            or 'erro nao especificado'
        )
        metadata = erro.get('metadata')
        if not mensagem and isinstance(metadata, dict):
            mensagem = metadata.get('raw') or metadata.get('provider_error_code')
    elif erro:
        mensagem = str(erro)
    else:
        mensagem = 'resposta invalida'

    return str(mensagem).strip()[:300] or 'erro nao especificado'


def _codigo_erro(dados):
    """Devolve o codigo de erro quando presente no corpo da resposta."""
    erro = dados.get('error') if isinstance(dados, dict) else None
    if isinstance(erro, dict):
        return erro.get('code') or erro.get('provider_error_code')
    return None


def _erro_de_contexto(dados):
    erro = dados.get('error') if isinstance(dados, dict) else None
    if not erro:
        return False
    codigo = str(_codigo_erro(dados) or '').casefold()
    mensagem = _detalhes_erro(dados).casefold()
    marcadores = (
        'context_length', 'context length', 'context window',
        'maximum context', 'max context', 'prompt is too long',
        'prompt_too_long', 'input token limit', 'too many tokens',
    )
    return (
        any(marcador in codigo for marcador in marcadores)
        or any(marcador in mensagem for marcador in marcadores)
    )


def _classificar_resposta(resposta):
    """Valida a resposta e classifica falhas para permitir o fallback.

    O OpenRouter pode devolver HTTP 200 com um corpo ``{"error": ...}`` quando
    o provider upstream falha. Por isso, o estado HTTP isoladamente nao basta
    para considerar a chamada bem-sucedida.
    """
    try:
        dados = resposta.json()
    except (TypeError, ValueError):
        dados = None

    status = getattr(resposta, 'status_code', 0)
    codigo = _codigo_erro(dados)

    if isinstance(dados, dict) and dados.get('error'):
        if _erro_de_contexto(dados):
            return 'contexto', _detalhes_erro(dados)
        if status == 429 or str(codigo) == '429':
            return 'rate_limit', _detalhes_erro(dados)
        if status == 404 or str(codigo) == '404':
            return 'modelo_indisponivel', _detalhes_erro(dados)
        return 'servico', _detalhes_erro(dados)

    if status == 429:
        return 'rate_limit', 'rate limit excedido'
    if status == 404:
        return 'modelo_indisponivel', 'modelo nao encontrado'
    if status >= 400:
        return 'servico', f'HTTP {status}'
    if not isinstance(dados, dict):
        return 'servico', 'resposta JSON invalida'

    escolhas = dados.get('choices')
    if not isinstance(escolhas, list) or not escolhas:
        return 'servico', 'resposta sem escolhas'

    escolha = escolhas[0]
    if not isinstance(escolha, dict):
        return 'servico', 'escolha invalida'

    mensagem = escolha.get('message')
    if not isinstance(mensagem, dict):
        return 'servico', 'mensagem invalida'

    conteudo = mensagem.get('content')
    tool_calls = mensagem.get('tool_calls')
    if tool_calls is not None and not isinstance(tool_calls, list):
        return 'servico', 'tool calls invalidos'

    tem_conteudo = isinstance(conteudo, str) and bool(conteudo.strip())
    if not tem_conteudo and not tool_calls:
        return 'servico', 'resposta sem conteudo nem tool calls'

    return 'ok', dados


def _registar_falha(modelo, motivo):
    """Regista uma falha de modelo sem expor credenciais ou payloads."""
    print(f'[Assistente] Modelo {modelo} indisponivel: {motivo}')


def _registar_uso(modelo, dados, bytes_entrada, limite_saida):
    """Regista tamanhos/uso sem guardar mensagens, ferramentas ou conteúdo."""
    uso = dados.get('usage') if isinstance(dados, dict) else None
    prompt_tokens = uso.get('prompt_tokens') if isinstance(uso, dict) else None
    completion_tokens = uso.get('completion_tokens') if isinstance(uso, dict) else None
    print(
        '[Assistente TOKENS] '
        f'modelo={modelo} bytes_entrada={bytes_entrada} '
        f'prompt_tokens={prompt_tokens if prompt_tokens is not None else "n/d"} '
        f'completion_tokens={completion_tokens if completion_tokens is not None else "n/d"} '
        f'limite_saida={limite_saida}'
    )


# Este é o limite da saída solicitada ao modelo, não o limite de contexto da
# entrada. O uso real de entrada é registado a partir do campo `usage` do provider.
_MAX_TOKENS_POR_OMISSAO = 1000


def _max_tokens():
    """Limite de tokens de saida, configuravel por env ou omissao."""
    try:
        valor = int(os.environ.get('OPENROUTER_MAX_TOKENS', _MAX_TOKENS_POR_OMISSAO))
    except (TypeError, ValueError):
        return _MAX_TOKENS_POR_OMISSAO
    return valor if valor > 0 else _MAX_TOKENS_POR_OMISSAO


def chamar_llm(mensagens, ferramentas=None, prazo_total=None, max_tokens=None):
    """Chama a API OpenRouter com retry e fallback automatico.

    Para cada modelo disponivel, sao feitas até ``_MAX_TENTATIVAS`` em caso de
    erro de rede. Erros HTTP, erros no corpo da resposta e respostas sem
    escolhas passam imediatamente ao modelo seguinte.

    Args:
        mensagens: lista de dicts no formato OpenAI (role, content).
        ferramentas: lista de tool definitions (opcional).
        prazo_total: prazo total em segundos (opcional). Quando definido, o
            tempo total da chamada — tentativas e modelos — respeita este
            valor: as esperas de backoff sao cortadas e o timeout de cada
            pedido e limitado ao tempo restante. None (omissao) mantem o
            comportamento historical do Assistente, sem prazo.
        max_tokens: limite de tokens de saida (opcional). Quando omitido, usa
            a variavel de ambiente ``OPENROUTER_MAX_TOKENS`` ou o default de
            1000. Modelos de raciocínio consomem parte do orçamento em
            ``reasoning`` antes do ``content``, pelo que um valor muito baixo
            pode deixar a resposta vazia.

    Returns:
        dict com a resposta da API.

    Raises:
        ValueError: chave de API nao configurada.
        RateLimitError: todos os modelos devolveram rate limit.
        ServicoIndisponivelError: todos os modelos falharam por indisponibilidade.
        PrazoExcedidoError: ``prazo_total`` expirou antes de haver resposta.
    """
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key or not api_key.strip():
        raise ValueError('OPENROUTER_API_KEY nao configurada.')

    prazo_fim = time.monotonic() + prazo_total if prazo_total else None

    def tempo_restante():
        if prazo_fim is None:
            return None
        return prazo_fim - time.monotonic()

    limite_tokens = max_tokens if max_tokens is not None else _max_tokens()

    entrada_serializavel = {'messages': mensagens}
    if ferramentas:
        entrada_serializavel['tools'] = ferramentas
    bytes_entrada = len(json.dumps(
        entrada_serializavel, ensure_ascii=False, separators=(',', ':')
    ).encode('utf-8'))

    payload_base = {
        'messages': mensagens,
        'max_tokens': limite_tokens,
    }
    if ferramentas:
        payload_base['tools'] = ferramentas

    rate_limit_excedido = False
    servico_indisponivel = False
    modelos_contexto_excedido = 0

    modelos = _listar_modelos()
    for modelo in modelos:
        payload = dict(payload_base, model=modelo)

        for i, espera in enumerate(_ESPERA_RETRY):
            restante = tempo_restante()
            if restante is not None and restante <= 0:
                raise PrazoExcedidoError(
                    f'Prazo total de {prazo_total:.0f}s excedido antes de '
                    'haver resposta.')
            timeout_pedido = 60 if restante is None else min(60, restante)
            try:
                resposta = requests.post(
                    OPENROUTER_URL,
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                    },
                    json=payload,
                    timeout=timeout_pedido,
                )
            except requests.RequestException as erro:
                if i < len(_ESPERA_RETRY) - 1:
                    restante = tempo_restante()
                    if restante is not None and espera >= restante:
                        raise PrazoExcedidoError(
                            f'Prazo total de {prazo_total:.0f}s excedido '
                            'durante o backoff de rede.') from erro
                    time.sleep(espera)
                    continue

                motivo = str(erro)[:300] or 'erro de rede'
                _registar_falha(modelo, motivo)
                servico_indisponivel = True
                break

            categoria, motivo = _classificar_resposta(resposta)
            if categoria == 'ok':
                _registar_uso(motivo.get('model', modelo), motivo,
                              bytes_entrada, limite_tokens)
                return motivo

            _registar_falha(modelo, motivo)
            if categoria == 'contexto':
                modelos_contexto_excedido += 1
            elif categoria == 'rate_limit':
                rate_limit_excedido = True
            else:
                servico_indisponivel = True
            # Erros de provider/modelo nao beneficiam de retry no mesmo modelo;
            # o fallback deve chegar rapidamente a um provider alternativo.
            break

    if modelos_contexto_excedido == len(modelos):
        raise ContextoExcedidoError(
            'Todos os modelos rejeitaram o tamanho do contexto do pedido.')

    if rate_limit_excedido and not servico_indisponivel:
        raise RateLimitError('Todos os modelos estao com rate limit excedido.')

    raise ServicoIndisponivelError(
        'Nenhum modelo conseguiu processar o pedido neste momento.'
    )
