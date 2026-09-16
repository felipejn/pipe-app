"""Cliente HTTP para a API OpenRouter com retry e fallback entre modelos gratuitos."""

import os
import time

import requests

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

_MAX_TENTATIVAS = 3
_ESPERA_RETRY = [2, 5, 10]  # segundos de backoff entre tentativas


def _listar_modelos():
    """Devolve lista de modelos gratuitos disponiveis, ordenados por preferencia."""
    padrao = os.environ.get('OPENROUTER_MODEL', 'google/gemma-4-31b-it:free')
    fallbacks = [m for m in [
        'google/gemma-4-31b-it:free',
        'nvidia/nemotron-3-super-120b-a12b:free',
        'cohere/north-mini-code:free',
        'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free',
    ] if m != padrao]
    return [padrao] + fallbacks


def chamar_llm(mensagens, ferramentas=None):
    """Chama a API OpenRouter com retry e fallback automatico.

    Para cada modelo disponivel, tenta ate _MAX_TENTATIVAS com backoff
    antes de passar ao proximo modelo da lista.

    Args:
        mensagens: lista de dicts no formato OpenAI (role, content).
        ferramentas: lista de tool definitions (opcional).

    Returns:
        dict com a resposta da API.

    Raises:
        requests.RequestException: erros de rede ou HTTP >= 400.
        ValueError: chave de API nao configurada.
        RateLimitError: todos os modelos com rate limit esgotado.
    """
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError('OPENROUTER_API_KEY nao configurada.')

    payload_base = {
        'messages': mensagens,
    }
    if ferramentas:
        payload_base['tools'] = ferramentas

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
            except requests.RequestException:
                if i < len(_ESPERA_RETRY) - 1:
                    time.sleep(espera)
                continue

            if resposta.status_code == 429:
                # Rate limit — passa imediatamente ao proximo modelo
                break

            if resposta.status_code == 404:
                # Modelo nao existe — passa ao proximo
                break

            resposta.raise_for_status()
            return resposta.json()

    raise RateLimitError('Todos os modelos estao com rate limit excedido.')


class RateLimitError(Exception):
    """Erro quando todos os modelos gratuitos estao com rate limit excedido."""
    pass
