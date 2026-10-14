#!/usr/bin/env python
"""Diagnóstico do canal Telegram do PIPE — token, chats e envio real.

Responde, sem ambiguidades, às três perguntas que um `telegram=False` no log da
scheduled task deixa em aberto:

  1. O token do bot é válido?          → GET /getMe
  2. O bot alcança cada utilizador?    → GET /getChat por chat_id da BD
  3. Um envio real passa?              → POST /sendMessage (--enviar-teste)

O `getChat` é o que apanha os dois casos permanentes mais comuns: o bot foi
bloqueado pelo utilizador («Forbidden: bot was blocked by the user») e o
`chat_id` deixou de existir («Bad Request: chat not found») — ambos devolvem
`False` no canal sem dizer porquê.

Credenciais lidas do .env (TELEGRAM_BOT_TOKEN).

Uso:
    python scripts/verificar_telegram.py                 # token + chats da BD
    python scripts/verificar_telegram.py --enviar-teste  # e envia uma mensagem
    python scripts/verificar_telegram.py --chat 123456   # testa um chat_id só
"""
import argparse
import os
import sys

import requests
from dotenv import load_dotenv

# Caminho do projecto no sys.path (para importar a app e ler os chat_ids)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE = 'https://api.telegram.org'
TIMEOUT = 15


def _carregar_token():
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        sys.exit('TELEGRAM_BOT_TOKEN em falta no .env')
    return token


def _chamar(token, metodo, params=None, json=None):
    """Chama a Bot API e devolve (dados, erro) — nunca levanta excepção."""
    url = f'{BASE}/bot{token}/{metodo}'
    try:
        resposta = requests.post(url, params=params, json=json, timeout=TIMEOUT)
    except requests.RequestException as erro:
        return None, f'Erro de rede: {erro}'
    try:
        dados = resposta.json()
    except (TypeError, ValueError):
        return None, f'HTTP {resposta.status_code} — corpo não-JSON'

    if dados.get('ok'):
        return dados.get('result'), None

    # A Bot API do Telegram põe `description` no topo do corpo (ao contrário da
    # OpenRouter, que a aninha em `error`); aceitam-se as duas formas.
    descricao = dados.get('description')
    if not descricao:
        erro = dados.get('error')
        if isinstance(erro, dict):
            descricao = erro.get('description') or erro.get('message')
        elif erro:
            descricao = str(erro)
    codigo = dados.get('error_code') or resposta.status_code
    descricao = str(descricao or 'motivo não indicado').strip()[:200]
    return None, f'HTTP {codigo} — {descricao}'


def verificar_token(token):
    """getMe: confirma que o token é válido e identifica o bot."""
    print('── Token ──')
    resultado, erro = _chamar(token, 'getMe')
    if erro:
        print(f'   INVÁLIDO ou inacessível: {erro}')
        print('   → token revogado/errado no BotFather, ou rede do PA em baixo.')
        return False
    print(f'   válido — bot @{resultado.get("username")} '
          f'(id {resultado.get("id")}, «{resultado.get("first_name")}»)')
    return True


def _chats_da_bd(apenas_chat=None):
    """chat_ids dos utilizadores activos, lidos da BD (username, chat, activo)."""
    from app import create_app, db
    from app.auth.models import User
    from app.notifications.models import UserNotificationPreferences

    app = create_app()
    with app.app_context():
        linhas = db.session.query(User, UserNotificationPreferences).join(
            UserNotificationPreferences,
            UserNotificationPreferences.user_id == User.id,
        ).filter(User.activo.is_(True)).all()
        alvos = [(u.username, (p.telegram_chat_id or '').strip(),
                  bool(p.telegram_activo)) for u, p in linhas]
    if apenas_chat:
        alvos = [a for a in alvos if a[1] == str(apenas_chat)]
    return alvos


def verificar_chats(token, apenas_chat=None):
    """getChat por chat_id: o bot consegue falar com cada um?"""
    print('\n── Chats (BD) ──')
    try:
        alvos = _chats_da_bd(apenas_chat)
    except Exception as erro:  # a BD pode não estar acessível nesta shell
        print(f'   não foi possível ler a BD: {erro}')
        return
    if not alvos:
        print('   nenhum utilizador com chat_id guardado.')
        return

    problematicos = 0
    for username, chat_id, activo in alvos:
        estado = 'on' if activo else 'off'
        if not chat_id:
            print(f'   {username}: sem chat_id de Telegram (canal {estado})')
            continue
        _, erro = _chamar(token, 'getChat', params={'chat_id': chat_id})
        if erro:
            problematicos += 1
            print(f'   {username} [{estado}] chat {chat_id}: FALHA — {erro}')
        else:
            print(f'   {username} [{estado}] chat {chat_id}: acessível')
    if problematicos:
        print(f'\n   {problematicos} chat(s) inacessível(is): corrige o chat_id em '
              f'/settings/notificacoes ou pede ao utilizador que reenvie uma '
              f'mensagem ao bot (um chat bloqueado tem de ser retomado por ele).')


def enviar_teste(token, apenas_chat=None):
    """sendMessage real — confirma que a entrega passa e mostra o motivo se não."""
    print('\n── Envio de teste ──')
    try:
        alvos = _chats_da_bd(apenas_chat)
    except Exception as erro:
        print(f'   não foi possível ler a BD: {erro}')
        return
    destinatarios = [a for a in alvos if a[1]]
    if not destinatarios:
        print('   nenhum chat_id para testar.')
        return

    texto = ('✅ PIPE — teste de diagnóstico do Telegram.\n'
             'Se estás a ler isto, o canal funciona.')
    for username, chat_id, _ in destinatarios:
        resultado, erro = _chamar(token, 'sendMessage', json={
            'chat_id': chat_id, 'text': texto, 'parse_mode': 'HTML',
        })
        if erro:
            print(f'   {username} ({chat_id}): FALHA — {erro}')
        else:
            print(f'   {username} ({chat_id}): enviada '
                  f'(message_id {resultado.get("message_id")})')


def main():
    parser = argparse.ArgumentParser(
        description='Diagnóstico do canal Telegram do PIPE')
    parser.add_argument('--enviar-teste', action='store_true',
                        help='envia uma mensagem real a cada chat_id da BD')
    parser.add_argument('--chat', default=None,
                        help='restringe o diagnóstico a um chat_id')
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    token = _carregar_token()
    if not verificar_token(token):
        return
    verificar_chats(token, args.chat)
    if args.enviar_teste:
        enviar_teste(token, args.chat)


if __name__ == '__main__':
    main()

