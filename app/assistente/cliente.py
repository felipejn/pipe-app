"""Cliente HTTP para a API OpenRouter com retry e fallback entre modelos gratuitos."""

import os
import time

import requests

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

_MAX_TENTATIVAS = 3
_ESPERA_RETRY = [2, 5, 10]  # segundos de backoff entre tentativas
_MODELOS_FALLBACK = [
    'nex-agi/nex-n2.5-mini:free',
    'inclusionai/ling-3.0-flash-sante:free',
    'liquid/lfm-2.5-2.6b:free',
    'nvidia/nemotron-3-super-120b-a12b:free',
    'nvidia/nemotron-3-ultra-550b-a55b:free',
]


class RateLimitError(Exception):
    """Erro quando todos os modelos gratuitos estao com rate limit excedido."""


class ServicoIndisponivelError(Exception):
    """Erro quando nenhum modelo conseguiu processar o pedido."""


def _listar_modelos():
    """Devolve lista de modelos gratuitos disponiveis, ordenados por preferencia."""
    padrao = os.environ.get('OPENROUTER_MODEL') or 'inclusionai/ling-3.0-flash-fin:free'
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


def chamar_llm(mensagens, ferramentas=None):
    """Chama a API OpenRouter com retry e fallback automatico.

    Para cada modelo disponivel, sao feitas até ``_MAX_TENTATIVAS`` em caso de
    erro de rede. Erros HTTP, erros no corpo da resposta e respostas sem
    escolhas passam imediatamente ao modelo seguinte.

    Args:
        mensagens: lista de dicts no formato OpenAI (role, content).
        ferramentas: lista de tool definitions (opcional).

    Returns:
        dict com a resposta da API.

    Raises:
        ValueError: chave de API nao configurada.
        RateLimitError: todos os modelos devolveram rate limit.
        ServicoIndisponivelError: todos os modelos falharam por indisponibilidade.
    """
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key or not api_key.strip():
        raise ValueError('OPENROUTER_API_KEY nao configurada.')

    payload_base = {
        'messages': mensagens,
        'max_tokens': 1000,
    }
    if ferramentas:
        payload_base['tools'] = ferramentas

    rate_limit_excedido = False
    servico_indisponivel = False

    for modelo in _listar_modelos():
        payload = dict(payload_base, model=modelo)

        for i, espera in enumerate(_ESPERA_RETRY):
            try:
                resposta = requests.post(
                    OPENROUTER_URL,
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                    },
                    json=payload,
                    timeout=60,
                )
            except requests.RequestException as erro:
                if i < len(_ESPERA_RETRY) - 1:
                    time.sleep(espera)
                    continue

                motivo = str(erro)[:300] or 'erro de rede'
                _registar_falha(modelo, motivo)
                servico_indisponivel = True
                break

            categoria, motivo = _classificar_resposta(resposta)
            if categoria == 'ok':
                return motivo

            _registar_falha(modelo, motivo)
            if categoria == 'rate_limit':
                rate_limit_excedido = True
            else:
                servico_indisponivel = True
            # Erros de provider/modelo nao beneficiam de retry no mesmo modelo;
            # o fallback deve chegar rapidamente a um provider alternativo.
            break

    if rate_limit_excedido and not servico_indisponivel:
        raise RateLimitError('Todos os modelos estao com rate limit excedido.')

    raise ServicoIndisponivelError(
        'Nenhum modelo conseguiu processar o pedido neste momento.'
    )
